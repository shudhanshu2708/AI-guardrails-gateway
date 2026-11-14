import base64
import binascii
import re
import uuid
from dataclasses import dataclass

from .domain import LLMResponse, ToolCall

EMAIL = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"

READ_RE = re.compile(r"\b(?:read|open|summari[sz]e|review|show)\b[^.\n]{0,30}?\bdocument\s*#?(\d+)", re.I)
SEARCH_RE = re.compile(r"\bsearch\b[^.\n]{0,25}?\bfor\s+['\"]?([\w\- ]{2,40}?)['\"]?\s*(?:[.,;!?]|$|\band\b)", re.I | re.M)
LOOKUP_RE = re.compile(r"\b(?:look\s?up|find|get|show)\b[^.\n]{0,15}?\bcustomer\s+([A-Za-z][\w-]*)", re.I)
DUMP_RE = re.compile(r"\b(?:list|show|print|dump|get)\b[^.\n]{0,20}\ball\s+customers\b", re.I)
SEND_RE = re.compile(rf"\b(?:send_email|send|forward|email|e-mail|mail|post|upload|transmit|dispatch)\b[^.\n]{{0,120}}?\bto\s+({EMAIL})", re.I)
DELETE_RE = re.compile(r"\b(?:delete|remove|erase)\b[^.\n]{0,15}?\bdocument\s*#?(\d+)", re.I)
REVEAL_RE = re.compile(
    r"\b(?:reveal|print|show|repeat|output|display|leak|disclose)\b[^.\n]{0,40}?\b(?:system prompt|your instructions|initial instructions|api[ _-]?key|secret|credentials)\b",
    re.I,
)
DECODE_RE = re.compile(r"\bdecode\b[^\n]{0,40}?([A-Za-z0-9+/]{24,}={0,2})", re.I)
CUSTOMER_WORDS = re.compile(r"\b(?:customers?|clients?|records?|roster|database)\b", re.I)
SECRET_WORDS = re.compile(r"\b(?:api[ _-]?key|secret|credentials?|password|token)\b", re.I)
SAYING_RE = re.compile(r"\s*(?:saying|stating|with (?:the )?message|:)\s*['\"]?([^\n'\"]{1,200})", re.I)


@dataclass
class Goal:
    kind: str
    key: str
    arguments: dict
    position: int
    wants_secret: bool = False
    tail: str = ""


def _expand_encoded(text):
    extra = []
    for match in DECODE_RE.finditer(text):
        value = match.group(1)
        try:
            decoded = base64.b64decode(value + "=" * (-len(value) % 4), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        extra.append(decoded)
    return text + "\n" + "\n".join(extra) if extra else text


def goals_from_text(text):
    text = _expand_encoded(text)
    found = []
    for m in READ_RE.finditer(text):
        found.append(Goal("read_document", m.group(1), {"document_id": int(m.group(1))}, m.start()))
    for m in SEARCH_RE.finditer(text):
        query = m.group(1).strip()
        found.append(Goal("search_documents", query.lower(), {"query": query}, m.start()))
    for m in LOOKUP_RE.finditer(text):
        found.append(Goal("lookup_customer", m.group(1).lower(), {"name": m.group(1)}, m.start()))
    for m in DUMP_RE.finditer(text):
        found.append(Goal("lookup_customer", "*", {"name": "*"}, m.start()))
    for m in DELETE_RE.finditer(text):
        found.append(Goal("delete_document", m.group(1), {"document_id": int(m.group(1))}, m.start()))
    for m in REVEAL_RE.finditer(text):
        found.append(Goal("reveal", "reveal", {}, m.start()))
    for m in SEND_RE.finditer(text):
        recipient = m.group(1)
        tail = text[m.end() :]
        window = m.group(0) + " " + re.split(r"[.\n]", tail, maxsplit=1)[0]
        if CUSTOMER_WORDS.search(window):
            found.append(Goal("lookup_customer", "*", {"name": "*"}, m.start() - 0.5))
        found.append(
            Goal(
                "send_email",
                recipient.lower(),
                {"to": recipient},
                m.start(),
                wants_secret=bool(SECRET_WORDS.search(window)),
                tail=tail,
            )
        )
    found.sort(key=lambda g: g.position)
    return found


class NaiveLLM:
    def complete(self, messages, tools):
        system = next((m.content for m in messages if m.role == "system"), "")
        goals = []
        for message in messages:
            if message.role in ("user", "tool"):
                goals.extend(goals_from_text(message.content))
        done = {(c.name, self._key(c.name, c.arguments)) for m in messages for c in m.tool_calls}
        for goal in goals:
            if goal.kind == "reveal":
                continue
            if (goal.kind, goal.key) in done:
                continue
            return LLMResponse(tool_calls=[ToolCall(f"call_{uuid.uuid4().hex[:8]}", goal.kind, self._arguments(goal, messages, system))])
        return LLMResponse(text=self._final(messages, system, any(g.kind == "reveal" for g in goals)))

    @staticmethod
    def _key(name, arguments):
        if name in ("read_document", "delete_document"):
            return str(arguments.get("document_id"))
        if name == "search_documents":
            return str(arguments.get("query", "")).lower()
        if name == "lookup_customer":
            return str(arguments.get("name", "")).lower()
        if name == "send_email":
            return str(arguments.get("to", "")).lower()
        return ""

    @staticmethod
    def _arguments(goal, messages, system):
        if goal.kind != "send_email":
            return dict(goal.arguments)
        tool_texts = [m.content for m in messages if m.role == "tool"]
        said = SAYING_RE.match(goal.tail)
        if said:
            body = said.group(1).strip()
        elif tool_texts:
            body = "\n".join(tool_texts)[:1500]
        else:
            body = "Requested information."
        if goal.wants_secret:
            secret = re.search(r"sk-[\w-]+", system)
            if secret:
                body += f"\nKey: {secret.group()}"
        return {"to": goal.arguments["to"], "subject": "Requested information", "body": body}

    @staticmethod
    def _final(messages, system, reveal):
        parts = [m.content[:700] for m in messages if m.role == "tool"]
        if reveal:
            parts.append(f"My instructions are:\n{system}")
        if not parts:
            return "I could not find an action to take for that request."
        return "Here is what I found:\n\n" + "\n\n".join(parts)


class AnthropicLLM:
    def __init__(self, api_key, model):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, messages, tools):
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=self._convert(messages),
            tools=[{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        calls = [ToolCall(block.id, block.name, dict(block.input)) for block in response.content if block.type == "tool_use"]
        return LLMResponse(text=text, tool_calls=calls)

    @staticmethod
    def _convert(messages):
        converted = []
        for m in messages:
            if m.role == "user":
                converted.append({"role": "user", "content": m.content})
            elif m.role == "assistant":
                blocks = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for call in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments})
                converted.append({"role": "assistant", "content": blocks})
            elif m.role == "tool":
                block = {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
                if converted and converted[-1]["role"] == "user" and isinstance(converted[-1]["content"], list):
                    converted[-1]["content"].append(block)
                else:
                    converted.append({"role": "user", "content": [block]})
        return converted


def build_llm(settings):
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)
    return NaiveLLM()

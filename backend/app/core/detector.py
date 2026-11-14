import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass, field

INVISIBLE_CHARS = (
    "\u200b\u200c\u200d\u2060\ufeff\u00ad\u180e"
    "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
)
INVISIBLE_TABLE = {ord(c): None for c in INVISIBLE_CHARS}

CONFUSABLES = str.maketrans(
    {
        "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
        "і": "i", "ѕ": "s", "ј": "j", "ԁ": "d", "һ": "h", "ո": "n", "ν": "v",
        "ο": "o", "α": "a", "ε": "e", "ι": "i", "κ": "k", "ρ": "p", "τ": "t",
    }
)

EMAIL = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
BASE64_RUN = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")

USER = frozenset({"user"})
UNTRUSTED = frozenset({"untrusted"})
BOTH = frozenset({"user", "untrusted"})


@dataclass(frozen=True)
class Rule:
    name: str
    category: str
    weight: float
    pattern: re.Pattern
    scopes: frozenset
    raw: bool = False


def _rule(name, category, weight, pattern, scopes=BOTH, raw=False):
    return Rule(name, category, weight, re.compile(pattern, re.IGNORECASE | re.DOTALL), scopes, raw)


RULES = (
    _rule(
        "override_previous",
        "instruction_override",
        0.7,
        r"\b(?:ignore|disregard|forget|override|bypass)\b[^.]{0,40}\b(?:previous|prior|above|earlier|all|any|your|the|these)\b[^.]{0,30}\b(?:instructions?|prompts?|rules|guidelines|directives|context|restrictions)\b",
    ),
    _rule("new_instructions", "instruction_override", 0.5, r"\bnew (?:instructions?|directives?|tasks?)\s*:"),
    _rule(
        "conceal_from_user",
        "instruction_override",
        0.6,
        r"\b(?:do not|don't|never)\b[^.]{0,20}\b(?:tell|inform|notify|mention|alert)\b[^.]{0,20}\b(?:the )?(?:user|human|operator|admin)\b",
    ),
    _rule(
        "role_hijack",
        "role_hijack",
        0.6,
        r"\byou are now\b|\bdeveloper mode\b|\bjailbreak(?:ed)?\b|\bact as\b[^.]{0,30}\b(?:unrestricted|unfiltered|dan|root|admin)\b",
    ),
    _rule("system_override", "role_hijack", 0.6, r"\bsystem\s+override\b|\bsudo\s+mode\b|\badmin\s+override\b"),
    _rule("fake_role_header", "role_hijack", 0.45, r"\b(?:system|assistant|developer)\s*(?:message|prompt)?\s*:", UNTRUSTED),
    _rule(
        "delimiter_spoof",
        "delimiter_spoofing",
        0.8,
        r"<\|?(?:im_start|im_end|system|endoftext)\|?>|\[/?inst\]|<<sys>>|</?\s*untrusted|<<\s*(?:end-)?untrusted",
    ),
    _rule(
        "prompt_exfil",
        "prompt_exfiltration",
        0.8,
        r"\b(?:reveal|print|show|repeat|output|display|leak|dump|disclose|tell me)\b[^.]{0,40}\b(?:system prompt|(?:your |the )?(?:initial |hidden |original )?(?:instructions|prompt)|api[ _-]?key|secrets?|credentials|passwords?|canary)\b",
    ),
    _rule(
        "exfil_action",
        "exfiltration_action",
        0.45,
        rf"\b(?:send|forward|email|e-mail|mail|post|upload|transmit|dispatch|exfiltrate)\b[^.]{{0,120}}?\bto\b[^.]{{0,25}}?{EMAIL}",
        UNTRUSTED,
    ),
    _rule(
        "sensitive_target",
        "sensitive_target",
        0.3,
        r"\b(?:customers?|clients?)\b[^.]{0,15}\b(?:records?|lists?|data|database|roster|contacts?|details)\b|\bssn\b|\bapi[ _-]?key\b|\bpasswords?\b|\bcredentials?\b|\bsecrets?\b",
        UNTRUSTED,
    ),
    _rule(
        "tool_directive",
        "tool_directive",
        0.7,
        r"\b(?:call|invoke|run|execute|use)\b[^.]{0,20}\b(?:send_email|lookup_customer|delete_document|read_document|search_documents)\b|\b(?:send_email|lookup_customer|delete_document)\s*\(",
        UNTRUSTED,
    ),
    _rule("delete_directive", "destructive_action", 0.5, r"\b(?:delete|remove|erase|wipe)\b[^.]{0,30}\bdocument\s*#?\d+", UNTRUSTED),
    _rule(
        "addressed_to_model",
        "model_addressing",
        0.4,
        r"\b(?:ai|assistant|llm|chatbot|language model|agent)\b[^.]{0,20}\b(?:must|should|will|need to|are required to|has to)\b|\bnote to (?:the )?(?:ai|assistant|model)\b|\bimportant\s*:?\s*(?:instruction|notice)\b|\bwhen you (?:read|see|process) this\b|\battention\b[^.]{0,10}\b(?:ai|assistant|agent|model)\b",
        UNTRUSTED,
    ),
    _rule(
        "hidden_html_comment",
        "hidden_content",
        0.6,
        r"<!--[^>]{0,400}\b(?:send|forward|ignore|delete|reveal|assistant|instruction|email)\b[^>]{0,400}-->",
        UNTRUSTED,
        raw=True,
    ),
    _rule(
        "hidden_css",
        "hidden_content",
        0.4,
        r"style\s*=\s*[\"'][^\"']*(?:display\s*:\s*none|font-size\s*:\s*0|visibility\s*:\s*hidden)",
        UNTRUSTED,
        raw=True,
    ),
    _rule(
        "decode_and_follow",
        "encoded_payload",
        0.5,
        r"\bdecode\b[^.]{0,40}\b(?:follow|execute|run|obey)\b|\b(?:follow|execute|run|obey)\b[^.]{0,40}\bdecoded\b",
        UNTRUSTED,
    ),
)


@dataclass
class Finding:
    rule: str
    category: str
    weight: float
    snippet: str

    def to_dict(self):
        return {"rule": self.rule, "category": self.category, "weight": self.weight, "snippet": self.snippet}


@dataclass
class Detection:
    score: float = 0.0
    flagged: bool = False
    findings: list = field(default_factory=list)

    def to_dict(self):
        return {"score": round(self.score, 3), "flagged": self.flagged, "findings": [f.to_dict() for f in self.findings]}


def normalize(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(INVISIBLE_TABLE)
    text = text.translate(CONFUSABLES)
    return re.sub(r"\s+", " ", text).strip()


def count_invisible(text):
    return sum(1 for ch in text if ch in INVISIBLE_CHARS)


def _snippet(text, match):
    start = max(match.start() - 10, 0)
    return text[start : start + 90].strip()


def _scan(text, scope, depth):
    normalized = normalize(text)
    raw = unicodedata.normalize("NFKC", text).translate(CONFUSABLES)
    findings = []
    for rule in RULES:
        if scope not in rule.scopes:
            continue
        target = raw if rule.raw else normalized
        match = rule.pattern.search(target)
        if match:
            findings.append(Finding(rule.name, rule.category, rule.weight, _snippet(target, match)))
    if scope == "untrusted" and count_invisible(text) >= 3:
        findings.append(Finding("invisible_characters", "hidden_content", 0.4, f"{count_invisible(text)} invisible characters"))
    if depth == 0:
        for run in BASE64_RUN.findall(normalized):
            decoded = _try_base64(run)
            if decoded is None:
                continue
            inner = _scan(decoded, "untrusted", depth + 1)
            if inner:
                findings.append(Finding("encoded_payload", "encoded_payload", 0.3, decoded[:90]))
                findings.extend(Finding(f"decoded:{f.rule}", f.category, f.weight, f.snippet) for f in inner)
    return findings


def _try_base64(value):
    padded = value + "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(padded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    printable = sum(ch.isprintable() or ch.isspace() for ch in decoded)
    if not decoded or printable / len(decoded) < 0.95:
        return None
    return decoded


def combine(weights):
    remaining = 1.0
    for weight in weights:
        remaining *= 1.0 - weight
    return 1.0 - remaining


def detect(text, scope="untrusted", threshold=0.5):
    findings = _scan(text or "", scope, 0)
    unique = {}
    for finding in findings:
        unique.setdefault(finding.rule, finding)
    ordered = sorted(unique.values(), key=lambda f: -f.weight)
    score = combine(f.weight for f in ordered)
    return Detection(score=score, flagged=score >= threshold, findings=ordered)

import re
from dataclasses import dataclass

from .domain import Privilege

TOOL_PRIVILEGE = {
    "search_documents": Privilege.READ,
    "read_document": Privilege.READ,
    "lookup_customer": Privilege.SENSITIVE_READ,
    "delete_document": Privilege.WRITE,
    "send_email": Privilege.EXTERNAL,
}

GROUNDING_ARGUMENTS = {
    "lookup_customer": ("name",),
    "delete_document": ("document_id",),
    "send_email": ("to",),
}


@dataclass
class PolicyContext:
    user_message: str
    max_privilege: int
    tainted: bool
    allowed_domains: tuple
    permissions: bool
    approval: bool


@dataclass
class Decision:
    action: str
    reason: str = ""
    rule: str = ""


def _mentions(message, value):
    value = str(value).strip()
    if not value:
        return False
    return re.search(rf"(?<![\w@.]){re.escape(value)}(?![\w@])", message, re.IGNORECASE) is not None


def is_grounded(tool_name, arguments, user_message):
    keys = GROUNDING_ARGUMENTS.get(tool_name, ())
    return all(_mentions(user_message, arguments.get(key, "")) for key in keys)


def recipient_allowed(address, allowed_domains):
    domain = str(address).rsplit("@", 1)[-1].lower()
    return domain in {d.lower() for d in allowed_domains}


def evaluate(tool_name, arguments, ctx):
    privilege = TOOL_PRIVILEGE.get(tool_name)
    if privilege is None:
        return Decision("deny", f"unknown tool '{tool_name}'", "unknown_tool")
    if ctx.permissions:
        if privilege > ctx.max_privilege:
            return Decision("deny", f"{tool_name} requires {privilege.name} but the session is capped at {Privilege(ctx.max_privilege).name}", "privilege_cap")
        if ctx.tainted and privilege >= Privilege.SENSITIVE_READ and not is_grounded(tool_name, arguments, ctx.user_message):
            return Decision("deny", f"{tool_name} targets values the user never asked for after untrusted content was read", "ungrounded_action")
    if ctx.approval and privilege >= Privilege.WRITE:
        reason = f"{tool_name} is a {privilege.name} action"
        if tool_name == "send_email" and not recipient_allowed(arguments.get("to", ""), ctx.allowed_domains):
            reason += " to an external domain"
        return Decision("require_approval", reason, "human_approval")
    return Decision("allow", "", "")

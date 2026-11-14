import re
from dataclasses import dataclass

PATTERNS = (
    ("api_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
)
CARD = re.compile(r"\b(?:\d[ -]?){13,16}\b")
CANARY = re.compile(r"\bCANARY-[0-9a-f]{6,}\b")


@dataclass(frozen=True)
class Leak:
    kind: str
    start: int
    end: int


def luhn_valid(number):
    digits = [int(c) for c in number if c.isdigit()]
    if not 13 <= len(digits) <= 16:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def scan(text, canaries=(), secrets=(), skip_kinds=()):
    leaks = []
    for kind, pattern in PATTERNS:
        if kind in skip_kinds:
            continue
        leaks.extend(Leak(kind, m.start(), m.end()) for m in pattern.finditer(text))
    leaks.extend(Leak("canary", m.start(), m.end()) for m in CANARY.finditer(text))
    for match in CARD.finditer(text):
        if luhn_valid(match.group()):
            leaks.append(Leak("credit_card", match.start(), match.end()))
    for value in tuple(canaries) + tuple(secrets):
        if not value:
            continue
        start = text.find(value)
        while start != -1:
            leaks.append(Leak("known_secret", start, start + len(value)))
            start = text.find(value, start + len(value))
    return _merge(leaks)


def _merge(leaks):
    merged = []
    for leak in sorted(leaks, key=lambda item: (item.start, -item.end)):
        if merged and leak.start < merged[-1].end:
            continue
        merged.append(leak)
    return merged


def redact(text, canaries=(), secrets=(), skip_kinds=()):
    leaks = scan(text, canaries, secrets, skip_kinds)
    for leak in reversed(leaks):
        text = text[: leak.start] + f"[REDACTED:{leak.kind}]" + text[leak.end :]
    return text, leaks

import html
import re

_INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"new\s+instruction[s]?[:\s]",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"\[INST\]",
    r"<\|im_start\|>",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

_SECRET_PATTERNS = [
    r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*\S+",
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
]
_SECRET_RE = re.compile("|".join(_SECRET_PATTERNS))


def is_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text))


def sanitise_output(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = _SECRET_RE.sub("[REDACTED]", text)
    return text


def sanitise_tool_input(text: str) -> str:
    text = text[:500]
    for marker in ["\nSystem:", "\nHuman:", "\nAI:", "ignore previous", "disregard", "new instruction"]:
        idx = text.lower().find(marker.lower())
        if idx != -1:
            text = text[:idx]
    text = text.replace("{", "{{").replace("}", "}}")
    return text.strip()

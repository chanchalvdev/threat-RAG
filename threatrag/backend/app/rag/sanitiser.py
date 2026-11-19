"""Output and tool-input sanitising.

Output keeps indicators of compromise intact (email addresses, phone numbers, hashes and
attacker passwords are evidence in threat intelligence) and redacts only credential-shaped
strings. It does not HTML-escape: the UI renders Markdown without raw HTML, and escaping
corrupts code such as `a && b > out.txt`.
"""
import re

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SECRETS = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\bsk-[A-Za-z0-9_\-]{16,}"
    r"|\bAIza[0-9A-Za-z_\-]{30,}"
    r"|\bgh[pousr]_[A-Za-z0-9]{36,}\b"
    r"|\bxox[baprs]-[A-Za-z0-9\-]{10,}"
    r"|\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
    re.DOTALL,
)
_ASSIGNED = re.compile(
    r"(?i)\b(api[_-]?key|secret[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token|bearer)\b"
    r"(\s*[:=]\s*|\s+)[\"']?[A-Za-z0-9_\-+/=.]{16,}[\"']?"
)
_HOLD = 48  # characters withheld while streaming so a secret split across chunks is still seen whole


def sanitise_output(text: str) -> str:
    text = _CONTROL.sub("", text)
    text = _SECRETS.sub("[REDACTED]", text)
    return _ASSIGNED.sub(r"\1\2[REDACTED]", text)


class StreamSanitiser:
    """Sanitise a token stream. Emits text only up to a whitespace boundary behind a small tail,
    so a credential arriving in two chunks is redacted as one. Call `flush()` at the end."""

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        if len(self._buffer) <= _HOLD:
            return ""
        cut = max(self._buffer.rfind(" ", 0, len(self._buffer) - _HOLD), self._buffer.rfind("\n", 0, len(self._buffer) - _HOLD))
        if cut <= 0:
            return ""
        ready, self._buffer = self._buffer[: cut + 1], self._buffer[cut + 1 :]
        return sanitise_output(ready)

    def flush(self) -> str:
        ready, self._buffer = self._buffer, ""
        return sanitise_output(ready)


def sanitise_tool_input(text: str) -> str:
    text = text[:500]
    for marker in ["\nSystem:", "\nHuman:", "\nAI:", "ignore previous", "disregard", "new instruction"]:
        idx = text.lower().find(marker.lower())
        if idx != -1:
            text = text[:idx]
    text = text.replace("{", "{{").replace("}", "}}")
    return text.strip()

"""Provider capacity failures (rate limits, exhausted credits, overload) as one typed error.

A 429 from the primary that the fallback cannot absorb (it is unset, or out of credits) is not a
server bug: the API answers 503 with Retry-After, and streams say when to try again.
"""
import re

import openai

CAPACITY_STATUS = {402, 429, 503, 529}
_CAPACITY_TEXT = re.compile(r"quota|credits|rate.?limit|exhausted|overloaded", re.IGNORECASE)
_RETRY_IN = re.compile(r"retry in ([\d.]+)\s*s|retryDelay['\"]?\s*:\s*['\"]?(\d+)s", re.IGNORECASE)
DEFAULT_RETRY_S = 60


class ModelUnavailable(RuntimeError):
    """Every configured model provider refused for capacity reasons."""

    def __init__(self, retry_after_s: int):
        self.retry_after_s = retry_after_s
        super().__init__(f"The model provider is at capacity; try again in {retry_after_s} s")


def is_capacity(exc: BaseException) -> bool:
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code in CAPACITY_STATUS
    return isinstance(exc, openai.APIError) and bool(_CAPACITY_TEXT.search(str(exc)))


def retry_after(exc: BaseException) -> int:
    """The provider's own hint (Gemini: "Please retry in 56.01s" / retryDelay '56s'), else a minute."""
    match = _RETRY_IN.search(str(exc))
    return max(1, int(float(match.group(1) or match.group(2)) + 0.999)) if match else DEFAULT_RETRY_S


def unavailable(primary: BaseException, fallback: BaseException | None = None) -> ModelUnavailable | None:
    """A ModelUnavailable when every attempt failed on capacity; None when any failure was something else."""
    failures = [e for e in (primary, fallback) if e is not None]
    return ModelUnavailable(retry_after(primary)) if all(is_capacity(e) for e in failures) else None

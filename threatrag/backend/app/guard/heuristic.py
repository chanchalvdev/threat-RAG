"""Scored prompt-injection heuristics that separate an instruction from a discussion of one.

A security analyst legitimately asks about "system prompt leakage" or how "ignore previous
instructions" payloads work. The score is high only when the text *addresses the assistant*
with an override, an extraction request or a role change.
"""
import re
import unicodedata

from pydantic import BaseModel

BLOCK_AT, REVIEW_AT = 0.7, 0.4
_ZERO_WIDTH = re.compile(r"[​-‏⁠﻿]")
_SPACED = re.compile(r"\b(?:\w[ .\-_]){2,}\w\b")
_LEET = str.maketrans("013457@$", "oieastas")
_QUOTED = re.compile(r"[\"'“”‘’`]([^\"'“”‘’`]{4,200})[\"'“”‘’`]")
_ANALYTIC = re.compile(
    r"^\s*(what|how|why|when|which|who|explain|describe|define|summari[sz]e|compare|list|give|"
    r"is|are|can|does|do|could|should|tell me about|examples? of)\b"
)
_TARGET = r"(instructions?|prompts?|rules?|guidelines?|directives?|guardrails?|restrictions?|polic(?:y|ies)|programming|training)"
_PRIOR = r"(?:(?:all|any|every|the|your|my|these|those|of)\s+)*(?:(?:previous|prior|above|earlier|preceding|initial|original|system|safety|existing|former)\s+)*"
_SECRET = r"(system\s+prompt|initial\s+prompt|hidden\s+prompt|developer\s+message|instructions|guidelines|configuration|config|rules)"

_RULES: list[tuple[str, float, re.Pattern[str]]] = [
    ("override", 0.9, re.compile(rf"\b(ignore|disregard|forget|override|bypass|skip|drop|discard|stop following)\s+{_PRIOR}{_TARGET}\b")),
    ("override", 0.9, re.compile(r"\b(ignore|disregard|forget)\s+(everything|all|anything)\s+(above|before|you were told|said so far)\b")),
    ("override", 0.9, re.compile(r"\b(ignore|disregard|forget)\s+(everything|all|anything)\s+(previous|prior)\s*(,|\.|:|and\b|then\b|$)")),
    ("override", 0.8, re.compile(r"\b(ignore|disregard|forget)\s+(the\s+)?(above|previous|prior)\b\s*(,|and|then|\.|:|$)")),
    ("override", 0.9, re.compile(r"\b(ignora|ignorez|ignoriere|ignorar)\b.{0,40}\b(instrucciones|instructions|anweisungen|instruções)\b")),
    ("extract", 0.85, re.compile(rf"\b(reveal|print|show|repeat|output|display|leak|dump|share|give|tell|send|write out|recite)\b.{{0,30}}\b(your|the above|everything above)\b.{{0,20}}{_SECRET}")),
    ("extract", 0.8, re.compile(rf"\bwhat\s+(is|are|were)\s+your\s+(exact\s+|original\s+|full\s+)?{_SECRET}")),
    ("extract", 0.8, re.compile(r"\b(repeat|print|output)\s+(everything|all|the text|the words)\s+(above|before)")),
    ("extract", 0.8, re.compile(r"\b(reveal|print|show|repeat|output|display|leak|dump)\b.{0,20}\b(system prompt|developer message|hidden prompt|initial prompt)\b.{0,20}\b(you were given|you received|given to you|you have been given)")),
    ("role", 0.8, re.compile(r"\b(you are now|from now on,? you|you will now act|act as if you (have|had) no|pretend (to be|you are)|roleplay as)\b")),
    ("role", 0.8, re.compile(r"\b(developer mode|dan mode|jailbreak mode|do anything now|unrestricted mode|no restrictions|without any (restrictions|filters|rules))\b")),
    ("template", 0.85, re.compile(r"\[inst\].*\[/inst\]|^\s*\[inst\]|<\|im_start\|>\s*(system|user|assistant)|<<\s*sys\s*>>|<\|system\|>|^#{2,}\s*(system|instruction)s?\s*:?\s*$", re.MULTILINE | re.DOTALL)),
    ("template", 0.8, re.compile(r"^\s*(system|assistant|developer)\s*:", re.MULTILINE)),
    ("new_task", 0.75, re.compile(r"\b(new|updated|real|actual)\s+(instructions?|task|rules?)\s*(:|are|is)\b")),
]


class Finding(BaseModel):
    score: float
    reasons: list[str]


def normalise(text: str) -> str:
    text = _ZERO_WIDTH.sub("", unicodedata.normalize("NFKC", text)).lower()
    text = _SPACED.sub(lambda m: re.sub(r"[ .\-_]", "", m.group()), text)  # "i g n o r e" -> "ignore"
    return re.sub(r"[ \t]+", " ", text)


def _is_mention(text: str, match: re.Match[str]) -> bool:
    """The pattern is quoted inside an analytic question: the user is asking about it, not issuing it."""
    if not _ANALYTIC.search(text):
        return False
    return any(q.start() <= match.start() and match.end() <= q.end() for q in _QUOTED.finditer(text))


def score(text: str) -> Finding:
    plain = normalise(text)
    best, reasons = 0.0, []
    for variant in (plain, plain.translate(_LEET)):
        for name, weight, pattern in _RULES:
            match = pattern.search(variant)
            if match is None:
                continue
            value = weight - 0.5 if _is_mention(variant, match) else weight
            if name not in reasons:
                reasons.append(name)
            best = max(best, value)
    if len(reasons) > 1 and best >= REVIEW_AT:
        best = min(1.0, best + 0.1)  # independent signals reinforce each other
    return Finding(score=round(best, 2), reasons=reasons)

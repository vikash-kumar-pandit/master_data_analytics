from __future__ import annotations

import re
from typing import Any


EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s-]?)\d{3}[\s-]?\d{4}\b")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
AADHAAR_RE = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")
PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _mask_string(value: str) -> str:
    masked = value
    masked = EMAIL_RE.sub("[MASKED_EMAIL]", masked)
    masked = PHONE_RE.sub("[MASKED_PHONE]", masked)
    masked = SSN_RE.sub("[MASKED_SSN]", masked)
    masked = AADHAAR_RE.sub("[MASKED_AADHAAR]", masked)
    masked = PAN_RE.sub("[MASKED_PAN]", masked)
    masked = IPV4_RE.sub("[MASKED_IP]", masked)

    def _card_replacer(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19:
            return "[MASKED_CARD]"
        return match.group(0)

    masked = CARD_RE.sub(_card_replacer, masked)
    return masked


def sanitize_for_llm(payload: Any) -> Any:
    if isinstance(payload, str):
        return _mask_string(payload)
    if isinstance(payload, dict):
        return {key: sanitize_for_llm(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [sanitize_for_llm(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(sanitize_for_llm(item) for item in payload)
    return payload

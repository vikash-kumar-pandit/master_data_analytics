from __future__ import annotations

import re
from typing import Any

import polars as pl


EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_PATTERN = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
CARD_PATTERN = r"\b(?:\d[ -]*?){13,19}\b"

EMAIL_RE = re.compile(EMAIL_PATTERN)
PHONE_RE = re.compile(PHONE_PATTERN)
CARD_RE = re.compile(CARD_PATTERN)


def _mask_text(value: str) -> str:
    masked = EMAIL_RE.sub("[MASKED_EMAIL]", value)
    masked = PHONE_RE.sub("[MASKED_PHONE]", masked)

    def replace_card(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19:
            return "[MASKED_CARD]"
        return match.group(0)

    return CARD_RE.sub(replace_card, masked)


def mask_sensitive_data(df: pl.DataFrame) -> pl.DataFrame:
    masked_df = df.clone()

    for column in masked_df.columns:
        if masked_df[column].dtype == pl.Utf8:
            masked_df = masked_df.with_columns(pl.col(column).str.replace_all(EMAIL_PATTERN, "[MASKED_EMAIL]"))
            masked_df = masked_df.with_columns(pl.col(column).str.replace_all(PHONE_PATTERN, "[MASKED_PHONE]"))
            masked_df = masked_df.with_columns(pl.col(column).str.replace_all(CARD_PATTERN, "[MASKED_CARD]"))

    return masked_df


def sanitize_for_llm(payload: Any) -> Any:
    if isinstance(payload, str):
        return _mask_text(payload)
    if isinstance(payload, dict):
        return {key: sanitize_for_llm(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [sanitize_for_llm(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(sanitize_for_llm(item) for item in payload)
    return payload

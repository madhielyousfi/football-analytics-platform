"""Response validation, error classification, and rejection counting."""

from __future__ import annotations

from typing import Any


def split_valid(items: Any, id_field: str, label: str) -> tuple[list[dict[str, Any]], int]:
    """Partition an API list into valid records and a rejected count.

    A record is valid when it is a dict carrying a non-null business key.
    Raises ValueError when the envelope itself is not a list (structural
    failure — the whole batch is unusable, nothing is silently dropped).
    """
    if not isinstance(items, list):
        raise ValueError(f"Invalid {label} list in API response")
    valid = [item for item in items
             if isinstance(item, dict) and item.get(id_field) is not None]
    return valid, len(items) - len(valid)


def classify_error(exc: BaseException) -> str:
    """Map an exception to a stable operational category (no secrets)."""
    text = f"{type(exc).__name__}: {exc}".lower()
    if "401" in text or "unauthorized" in text:
        return "AUTH"
    if "429" in text or "quota" in text or "throttl" in text:
        return "RATE_LIMIT"
    if "403" in text or "plan" in text or "forbidden" in text:
        return "PLAN"
    if "timeout" in text or "connection" in text or "network" in text \
            or "request failed" in text:
        return "NETWORK"
    if "invalid" in text or "unexpected" in text or "missing" in text or "parse" in text:
        return "VALIDATION"
    return "UNKNOWN"

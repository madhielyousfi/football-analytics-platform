"""Current-season discovery from football-data.org competition metadata."""

from __future__ import annotations

from typing import Any


def discover_season(competitions: list[dict[str, Any]], code: str) -> int:
    """Return the current season starting year for a competition code.

    Reads ``currentSeason.startDate`` (``YYYY-MM-DD``) from the API's
    /competitions listing — never a hard-coded year. Raises ValueError with
    an actionable message when the competition or season is absent.
    """
    selected = next((item for item in competitions if item.get("code") == code), None)
    if selected is None:
        raise ValueError(
            f"Competition {code} absent from API /competitions response; "
            "check the code and plan access")
    current = selected.get("currentSeason") or {}
    start = current.get("startDate") or ""
    try:
        year = int(str(start)[:4])
    except (ValueError, TypeError):
        raise ValueError(
            f"Competition {code} has no parseable currentSeason.startDate "
            f"({start!r}); pass FOOTBALL_SEASON explicitly") from None
    if not 2000 <= year <= 2100:
        raise ValueError(
            f"Competition {code} reports implausible season start {start!r}; "
            "pass FOOTBALL_SEASON explicitly")
    return year

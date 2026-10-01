"""Map competition API objects into raw rows."""

from datetime import datetime, timezone
from typing import Any


def competition_rows(items: list[dict[str, Any]], batch_id: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [{"competition_id": item.get("id"), "name": item.get("name"),
             "code": item.get("code"), "type": item.get("type"),
             "area_name": (item.get("area") or {}).get("name"),
             "current_season_id": (item.get("currentSeason") or {}).get("id"),
             "_payload": item, "_ingested_at": now, "_batch_id": batch_id,
             "_source": "football-data.org", "_api_endpoint": "/competitions"}
            for item in items]

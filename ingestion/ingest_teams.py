"""Map team API objects into raw rows."""

from datetime import datetime, timezone
from typing import Any


def team_rows(items: list[dict[str, Any]], batch_id: str,
              competition_id: int, season: int, competition: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    endpoint = f"/competitions/{competition}/teams"
    return [{"team_id": item.get("id"), "name": item.get("name"),
             "short_name": item.get("shortName"), "tla": item.get("tla"),
             "country": (item.get("area") or {}).get("name"),
             "founded": item.get("founded"), "venue": item.get("venue"),
             "club_colors": item.get("clubColors"), "crest_url": item.get("crest"),
             "competition_id": competition_id, "_season": season,
             "_payload": item, "_ingested_at": now, "_batch_id": batch_id,
             "_source": "football-data.org", "_api_endpoint": endpoint}
            for item in items]

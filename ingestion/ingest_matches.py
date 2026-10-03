"""Map match API objects into raw rows."""

from datetime import datetime, timezone
from typing import Any


def match_rows(items: list[dict[str, Any]], batch_id: str,
               season: int, competition: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    endpoint = f"/competitions/{competition}/matches"
    rows = []
    for item in items:
        league = item.get("competition") or {}
        source_season = item.get("season") or {}
        score = item.get("score") or {}
        full_time = score.get("fullTime") or {}
        home = item.get("homeTeam") or {}
        away = item.get("awayTeam") or {}
        rows.append({
            "match_id": item.get("id"), "competition_id": league.get("id"),
            "competition_name": league.get("name"), "season_id": source_season.get("id"),
            "season_start_date": source_season.get("startDate"),
            "season_end_date": source_season.get("endDate"),
            "utc_date": item.get("utcDate"), "status": item.get("status"),
            "matchday": item.get("matchday"), "stage": item.get("stage"),
            "group_name": item.get("group"),
            "home_team_id": home.get("id"), "home_team_name": home.get("name"),
            "away_team_id": away.get("id"), "away_team_name": away.get("name"),
            "home_score": full_time.get("home"), "away_score": full_time.get("away"),
            "winner": score.get("winner"), "duration": score.get("duration"),
            "_season": season, "_competition": competition, "_payload": item,
            "_ingested_at": now, "_batch_id": batch_id,
            "_source": "football-data.org", "_api_endpoint": endpoint,
        })
    return rows

"""Flatten official API standing groups into keyed raw rows."""

from datetime import datetime, timezone
from typing import Any


def standing_rows(response: dict[str, Any], batch_id: str,
                  competition: str, season: int) -> list[dict[str, Any]]:
    """Keep TOTAL/HOME/AWAY and group standings separate by a stable key."""
    groups = response.get("standings", [])
    if not isinstance(groups, list):
        raise ValueError("Invalid standings list in API response")
    competition_id = (response.get("competition") or {}).get("id")
    season_id = (response.get("season") or {}).get("id")
    if competition_id is None:
        raise ValueError("Standing response is missing competition ID")
    now = datetime.now(timezone.utc)
    endpoint = f"/competitions/{competition}/standings"
    rows = []
    for group in groups:
        entries = group.get("table", [])
        if not isinstance(entries, list):
            raise ValueError("Invalid standing table in API response")
        standing_type = group.get("type")
        stage = group.get("stage")
        group_name = group.get("group")
        for entry in entries:
            team = entry.get("team") or {}
            team_id = team.get("id")
            if team_id is None or standing_type is None:
                raise ValueError("Standing row is missing team ID or type")
            key = f"{competition_id}:{season}:{standing_type}:{stage or ''}:{group_name or ''}:{team_id}"
            rows.append({
                "standing_key": key, "competition_id": competition_id,
                "season_id": season_id, "team_id": team_id,
                "team_name": team.get("name"), "standing_type": standing_type,
                "stage": stage, "group_name": group_name,
                "position": entry.get("position"), "played_games": entry.get("playedGames"),
                "won": entry.get("won"), "draw": entry.get("draw"),
                "lost": entry.get("lost"), "points": entry.get("points"),
                "goals_for": entry.get("goalsFor"), "goals_against": entry.get("goalsAgainst"),
                "goal_difference": entry.get("goalDifference"), "form": entry.get("form"),
                "_season": season, "_competition": competition, "_payload": entry,
                "_ingested_at": now, "_batch_id": batch_id,
                "_source": "football-data.org", "_api_endpoint": endpoint,
            })
    return rows

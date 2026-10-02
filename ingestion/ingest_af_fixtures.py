"""Map API-Football objects into raw_af rows."""

from datetime import datetime, timezone
from typing import Any


def fixture_rows(items: list[dict[str, Any]], batch_id: str) -> list[dict[str, Any]]:
    """Flatten /fixtures response items into raw_af.fixtures rows."""
    now = datetime.now(timezone.utc)
    rows = []
    for item in items:
        fixture = item.get("fixture") or {}
        league = item.get("league") or {}
        teams = item.get("teams") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        goals = item.get("goals") or {}
        status = fixture.get("status") or {}
        rows.append({
            "fixture_id": fixture.get("id"), "league_id": league.get("id"),
            "league_name": league.get("name"), "season": league.get("season"),
            "round": league.get("round"), "fixture_date": fixture.get("date"),
            "timestamp": fixture.get("timestamp"),
            "status_long": status.get("long"), "status_short": status.get("short"),
            "elapsed": status.get("elapsed"),
            "home_team_id": home.get("id"), "home_team_name": home.get("name"),
            "home_winner": home.get("winner"),
            "away_team_id": away.get("id"), "away_team_name": away.get("name"),
            "away_winner": away.get("winner"),
            "goals_home": goals.get("home"), "goals_away": goals.get("away"),
            "_payload": item, "_ingested_at": now, "_batch_id": batch_id,
            "_source": "api-football", "_api_endpoint": "/fixtures",
        })
    return rows


def event_key(fixture_id: Any, elapsed: Any, extra: Any, team_id: Any,
              player_id: Any, event_type: Any, detail: Any) -> str:
    return f"{fixture_id}:{elapsed}:{extra}:{team_id}:{player_id}:{event_type}:{detail}"


def event_rows(fixture_id: int, items: list[dict[str, Any]],
               batch_id: str) -> list[dict[str, Any]]:
    """Flatten /fixtures/events items into raw_af.events rows."""
    now = datetime.now(timezone.utc)
    rows = []
    for item in items:
        moment = item.get("time") or {}
        team = item.get("team") or {}
        player = item.get("player") or {}
        assist = item.get("assist") or {}
        elapsed, extra = moment.get("elapsed"), moment.get("extra")
        event_type, detail = item.get("type"), item.get("detail")
        rows.append({
            "event_key": event_key(fixture_id, elapsed, extra, team.get("id"),
                                   player.get("id"), event_type, detail),
            "fixture_id": fixture_id, "elapsed": elapsed, "extra_minute": extra,
            "team_id": team.get("id"), "team_name": team.get("name"),
            "player_id": player.get("id"), "player_name": player.get("name"),
            "assist_player_id": assist.get("id"), "assist_player_name": assist.get("name"),
            "event_type": event_type, "detail": detail,
            "comments": item.get("comments"),
            "_payload": item, "_ingested_at": now, "_batch_id": batch_id,
            "_source": "api-football", "_api_endpoint": "/fixtures/events",
        })
    return rows

"""Map API-Football depth objects (lineups, stats, players, odds) into rows."""

from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def lineup_rows(fixture_id: int, items: list[dict[str, Any]],
               batch_id: str) -> list[dict[str, Any]]:
    """Flatten /fixtures/lineups (one entry per team) into player-grain rows."""
    now, rows = _now(), []
    for entry in items:
        team = entry.get("team") or {}
        coach = entry.get("coach") or {}
        formation = entry.get("formation")
        for is_starting, key in ((True, "startXI"), (False, "substitutes")):
            for slot in entry.get(key) or []:
                player = slot.get("player") or {}
                rows.append({
                    "lineup_key": f"{fixture_id}:{team.get('id')}:{player.get('id')}:{int(is_starting)}",
                    "fixture_id": fixture_id,
                    "team_id": team.get("id"), "team_name": team.get("name"),
                    "formation": formation, "coach_name": coach.get("name"),
                    "player_id": player.get("id"), "player_name": player.get("name"),
                    "number": player.get("number"), "position": player.get("pos"),
                    "grid": player.get("grid"), "is_starting": is_starting,
                    "_payload": slot, "_ingested_at": now, "_batch_id": batch_id,
                    "_source": "api-football", "_api_endpoint": "/fixtures/lineups",
                })
    return rows


def fixture_stat_rows(fixture_id: int, items: list[dict[str, Any]],
                      batch_id: str) -> list[dict[str, Any]]:
    """Flatten /fixtures/statistics (one entry per team) into type-grain rows."""
    now, rows = _now(), []
    for entry in items:
        team = entry.get("team") or {}
        for stat in entry.get("statistics") or []:
            stat_type = stat.get("type")
            rows.append({
                "stat_key": f"{fixture_id}:{team.get('id')}:{stat_type}",
                "fixture_id": fixture_id,
                "team_id": team.get("id"), "team_name": team.get("name"),
                "stat_type": stat_type, "stat_value": stat.get("value"),
                "_payload": stat, "_ingested_at": now, "_batch_id": batch_id,
                "_source": "api-football", "_api_endpoint": "/fixtures/statistics",
            })
    return rows


def _nested(stats: dict[str, Any], *path: str) -> Any:
    node: Any = stats
    for key in path:
        node = (node or {}).get(key)
    return node


def player_stat_rows(fixture_id: int, items: list[dict[str, Any]],
                     batch_id: str) -> list[dict[str, Any]]:
    """Flatten /fixtures/players into player-grain rows with key metrics."""
    now, rows = _now(), []
    for entry in items:
        team = entry.get("team") or {}
        for slot in entry.get("players") or []:
            player = slot.get("player") or {}
            stats = slot.get("statistics") or [{}]
            st = stats[0] if stats else {}
            rows.append({
                "pstat_key": f"{fixture_id}:{player.get('id')}",
                "fixture_id": fixture_id,
                "team_id": team.get("id"), "team_name": team.get("name"),
                "player_id": player.get("id"), "player_name": player.get("name"),
                "number": player.get("number"), "position": player.get("pos"),
                "minutes": _nested(st, "games", "minutes"),
                "rating": _nested(st, "games", "rating"),
                "goals": _nested(st, "goals", "total"),
                "assists": _nested(st, "goals", "assists"),
                "shots_total": _nested(st, "shots", "total"),
                "shots_on": _nested(st, "shots", "on"),
                "passes_total": _nested(st, "passes", "total"),
                "passes_key": _nested(st, "passes", "key"),
                "passes_accuracy": _nested(st, "passes", "accuracy"),
                "tackles": _nested(st, "tackles", "total"),
                "interceptions": _nested(st, "tackles", "interceptions"),
                "duels_total": _nested(st, "duels", "total"),
                "duels_won": _nested(st, "duels", "won"),
                "dribbles_attempts": _nested(st, "dribbles", "attempts"),
                "dribbles_success": _nested(st, "dribbles", "success"),
                "fouls_drawn": _nested(st, "fouls", "drawn"),
                "fouls_committed": _nested(st, "fouls", "committed"),
                "yellow": _nested(st, "cards", "yellow"),
                "red": _nested(st, "cards", "red"),
                "_payload": slot, "_ingested_at": now, "_batch_id": batch_id,
                "_source": "api-football", "_api_endpoint": "/fixtures/players",
            })
    return rows


def odd_rows(fixture_id: int, items: list[dict[str, Any]],
             batch_id: str) -> list[dict[str, Any]]:
    """Flatten /odds (bookmaker -> bets -> values) into value-grain rows."""
    now, rows = _now(), []
    for entry in items:
        for bookmaker in entry.get("bookmakers") or []:
            for bet in bookmaker.get("bets") or []:
                for value in bet.get("values") or []:
                    rows.append({
                        "odd_key": f"{fixture_id}:{bookmaker.get('id')}:{bet.get('id')}:{value.get('value')}",
                        "fixture_id": fixture_id,
                        "bookmaker_id": bookmaker.get("id"),
                        "bookmaker_name": bookmaker.get("name"),
                        "bet_id": bet.get("id"), "bet_name": bet.get("name"),
                        "value_name": value.get("value"), "odd": value.get("odd"),
                        "_payload": {"bet": bet.get("name"), "value": value},
                        "_ingested_at": now, "_batch_id": batch_id,
                        "_source": "api-football", "_api_endpoint": "/odds",
                    })
    return rows


def injury_rows(items: list[dict[str, Any]], batch_id: str) -> list[dict[str, Any]]:
    """Flatten /injuries entries (player + team + fixture context)."""
    now, rows = _now(), []
    for entry in items:
        player = entry.get("player") or {}
        team = entry.get("team") or {}
        fixture = entry.get("fixture") or {}
        rows.append({
            "injury_key": f"{player.get('id')}:{team.get('id')}:{fixture.get('id')}",
            "player_id": player.get("id"), "player_name": player.get("name"),
            "injury_type": player.get("type"), "reason": player.get("reason"),
            "team_id": team.get("id"), "team_name": team.get("name"),
            "fixture_id": fixture.get("id"), "fixture_date": fixture.get("date"),
            "_payload": entry, "_ingested_at": now, "_batch_id": batch_id,
            "_source": "api-football", "_api_endpoint": "/injuries",
        })
    return rows

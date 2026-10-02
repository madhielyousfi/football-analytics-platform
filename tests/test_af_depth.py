"""API-Football depth loaders (lineups, stats, players, odds) offline."""

import duckdb

from ingestion import database as db
from ingestion.ingest_af_depth import (
    fixture_stat_rows,
    injury_rows,
    lineup_rows,
    odd_rows,
    player_stat_rows,
)

LINEUPS = [{
    "team": {"id": 50, "name": "Manchester City"},
    "coach": {"id": 4, "name": "P. Guardiola"},
    "formation": "4-3-3",
    "startXI": [{"player": {"id": 617, "name": "E. Haaland", "number": 9, "pos": "F", "grid": "4:3"}}],
    "substitutes": [{"player": {"id": 636, "name": "J. Álvarez", "number": 19, "pos": "F", "grid": None}}],
}]

STATS = [
    {"team": {"id": 50, "name": "Manchester City"},
     "statistics": [{"type": "Ball Possession", "value": "59%"},
                    {"type": "Total Shots", "value": "14"}]},
    {"team": {"id": 42, "name": "Arsenal"},
     "statistics": [{"type": "Ball Possession", "value": "41%"},
                    {"type": "Total Shots", "value": "9"}]},
]

PLAYERS = [{
    "team": {"id": 50, "name": "Manchester City"},
    "players": [{
        "player": {"id": 617, "name": "E. Haaland", "number": 9, "pos": "F"},
        "statistics": [{"games": {"minutes": 90, "rating": "8.4"},
                        "shots": {"total": 5, "on": 3},
                        "goals": {"total": 2, "assists": 0},
                        "passes": {"total": 18, "key": 1, "accuracy": "83%"},
                        "tackles": {"total": 1, "interceptions": 0},
                        "duels": {"total": 9, "won": 5},
                        "dribbles": {"attempts": 2, "success": 1},
                        "fouls": {"drawn": 2, "committed": 1},
                        "cards": {"yellow": 0, "red": 0}}],
    }],
}]

ODDS = [{
    "league": {"id": 39}, "fixture": {"id": 1},
    "bookmakers": [{"id": 6, "name": "Bwin",
                    "bets": [{"id": 1, "name": "Match Winner",
                              "values": [{"value": "Home", "odd": "1.55"},
                                         {"value": "Draw", "odd": "4.10"},
                                         {"value": "Away", "odd": "5.75"}]}]}],
}]


def memdb() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    db.create_tables(con)
    return con


def test_lineup_rows_starters_and_bench() -> None:
    starter, sub = lineup_rows(1, LINEUPS, "b")
    assert starter["is_starting"] is True and starter["grid"] == "4:3"
    assert starter["formation"] == "4-3-3" and starter["coach_name"] == "P. Guardiola"
    assert sub["is_starting"] is False and sub["grid"] is None
    assert starter["lineup_key"] != sub["lineup_key"]


def test_fixture_stat_rows_per_team_type() -> None:
    rows = fixture_stat_rows(1, STATS, "b")
    assert len(rows) == 4
    poss = [r for r in rows if r["stat_type"] == "Ball Possession"]
    assert {r["team_name"]: r["stat_value"] for r in poss} == {
        "Manchester City": "59%", "Arsenal": "41%"}


def test_player_stat_rows_flatten_metrics() -> None:
    (row,) = player_stat_rows(1, PLAYERS, "b")
    assert row["player_name"] == "E. Haaland" and row["minutes"] == 90
    assert row["rating"] == "8.4" and row["goals"] == 2
    assert row["shots_on"] == 3 and row["passes_accuracy"] == "83%"
    assert row["yellow"] == 0


def test_odd_rows_value_grain() -> None:
    rows = odd_rows(1, ODDS, "b")
    assert len(rows) == 3
    home = next(r for r in rows if r["value_name"] == "Home")
    assert home["odd"] == "1.55" and home["bookmaker_name"] == "Bwin"
    assert home["bet_name"] == "Match Winner"


INJURIES = [{
    "player": {"id": 617, "name": "E. Haaland", "type": "Injury", "reason": "Knee Injury"},
    "team": {"id": 50, "name": "Manchester City"},
    "fixture": {"id": 2, "date": "2026-08-23T14:00:00+00:00"},
}]


def test_injury_rows_flatten_context() -> None:
    (row,) = injury_rows(INJURIES, "b")
    assert row["player_name"] == "E. Haaland" and row["injury_type"] == "Injury"
    assert row["reason"] == "Knee Injury" and row["fixture_id"] == 2
    assert row["team_name"] == "Manchester City"


def test_depth_upsert_roundtrips() -> None:
    con = memdb()
    assert db.upsert_rows(con, "lineups", "lineup_key",
                          lineup_rows(1, LINEUPS, "b"), schema="raw_af")[0] == 2
    assert db.upsert_rows(con, "fixture_stats", "stat_key",
                          fixture_stat_rows(1, STATS, "b"), schema="raw_af")[0] == 4
    assert db.upsert_rows(con, "player_stats", "pstat_key",
                          player_stat_rows(1, PLAYERS, "b"), schema="raw_af")[0] == 1
    assert db.upsert_rows(con, "odds", "odd_key",
                          odd_rows(1, ODDS, "b"), schema="raw_af")[0] == 3
    assert db.upsert_rows(con, "injuries", "injury_key",
                          injury_rows(INJURIES, "b"), schema="raw_af")[0] == 1

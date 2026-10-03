"""group_name capture for cup tournaments (offline)."""

import duckdb

from ingestion import database as db
from ingestion.ingest_matches import match_rows


def test_match_rows_keep_group() -> None:
    (row,) = match_rows([{
        "id": 1, "utcDate": "2024-06-14T19:00:00Z", "status": "FINISHED",
        "matchday": 1, "stage": "GROUP_STAGE", "group": "GROUP_A",
        "competition": {"id": 2018}, "season": {"id": 1},
        "homeTeam": {"id": 10, "name": "Alpha"}, "awayTeam": {"id": 11, "name": "Beta"},
        "score": {"winner": "HOME_TEAM", "duration": "REGULAR",
                  "fullTime": {"home": 2, "away": 0}}},
    ], "batch-1", 2024, "EC")
    assert row["group_name"] == "GROUP_A"
    assert row["stage"] == "GROUP_STAGE"


def test_match_rows_group_defaults_none() -> None:
    (row,) = match_rows([{
        "id": 2, "utcDate": "2026-08-15T15:00:00Z", "status": "FINISHED",
        "matchday": 1, "stage": "REGULAR_SEASON",
        "competition": {"id": 2021}, "season": {"id": 2},
        "homeTeam": {"id": 1, "name": "A"}, "awayTeam": {"id": 2, "name": "B"},
        "score": {"winner": "DRAW", "duration": "REGULAR",
                  "fullTime": {"home": 1, "away": 1}}},
    ], "batch-1", 2026, "PL")
    assert row["group_name"] is None


def test_migration_adds_column_and_backfills_payload() -> None:
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA raw")
    # Simulate a pre-migration table without group_name.
    con.execute("""CREATE TABLE raw.matches (
        match_id INTEGER PRIMARY KEY, _payload JSON, group_name VARCHAR)""")
    con.execute("DROP TABLE raw.matches")
    con.execute("""CREATE TABLE raw.matches (
        match_id INTEGER PRIMARY KEY, _payload JSON)""")
    con.execute("""INSERT INTO raw.matches VALUES
        (1, '{"group": "GROUP_A"}'), (2, '{"stage": "REGULAR_SEASON"}')""")
    backfilled = db.ensure_raw_matches_group(con)
    assert backfilled == 1
    rows = dict(con.execute("SELECT match_id, group_name FROM raw.matches").fetchall())
    assert rows == {1: "GROUP_A", 2: None}
    # Idempotent on second run.
    assert db.ensure_raw_matches_group(con) == 0

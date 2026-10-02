"""API-Football loaders, raw_af upserts and team mapping (offline)."""

import duckdb

from ingestion import database as db
from ingestion.id_map import build_team_map, normalize_name, upsert_team_map
from ingestion.ingest_af_fixtures import event_rows, fixture_rows

FIXTURE = {
    "fixture": {"id": 867946, "date": "2023-09-16T16:30:00+00:00", "timestamp": 1694881800,
                "status": {"long": "Match Finished", "short": "FT", "elapsed": 90}},
    "league": {"id": 39, "name": "Premier League", "season": 2023, "round": "Regular Season - 5"},
    "teams": {"home": {"id": 50, "name": "Manchester City", "winner": True},
              "away": {"id": 42, "name": "Arsenal", "winner": False}},
    "goals": {"home": 3, "away": 1},
}

EVENTS = [
    {"time": {"elapsed": 36, "extra": None},
     "team": {"id": 50, "name": "Manchester City"},
     "player": {"id": 617, "name": "E. Haaland"},
     "assist": {"id": 635, "name": "K. De Bruyne"},
     "type": "Goal", "detail": "Normal Goal", "comments": None},
    {"time": {"elapsed": 90, "extra": 2},
     "team": {"id": 42, "name": "Arsenal"},
     "player": {"id": 98, "name": "B. Saka"},
     "assist": {"id": None, "name": None},
     "type": "Card", "detail": "Yellow Card", "comments": "Foul"},
]


def test_fixture_rows_flatten_envelope() -> None:
    (row,) = fixture_rows([FIXTURE], "batch-1")
    assert row["fixture_id"] == 867946
    assert row["league_id"] == 39 and row["season"] == 2023
    assert row["status_short"] == "FT" and row["elapsed"] == 90
    assert row["home_team_id"] == 50 and row["goals_home"] == 3
    assert row["_source"] == "api-football" and row["_api_endpoint"] == "/fixtures"


def test_event_rows_key_and_nullable_assist() -> None:
    goal, card = event_rows(867946, EVENTS, "batch-1")
    assert goal["event_key"].startswith("867946:36:")
    assert goal["assist_player_name"] == "K. De Bruyne"
    assert card["extra_minute"] == 2 and card["assist_player_id"] is None
    assert card["event_type"] == "Card"


def memdb() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    db.create_tables(con)
    return con


def test_raw_af_upsert_roundtrip_and_idempotent() -> None:
    con = memdb()
    rows = fixture_rows([FIXTURE], "batch-1")
    inserted, updated = db.upsert_rows(con, "fixtures", "fixture_id", rows, schema="raw_af")
    assert (inserted, updated) == (1, 0)
    inserted, updated = db.upsert_rows(con, "fixtures", "fixture_id", rows, schema="raw_af")
    assert (inserted, updated) == (0, 1)
    events = event_rows(867946, EVENTS, "batch-1")
    inserted, _ = db.upsert_rows(con, "events", "event_key", events, schema="raw_af")
    assert inserted == 2
    assert con.execute("SELECT COUNT(*) FROM raw_af.fixtures").fetchone()[0] == 1


def test_upsert_rejects_unknown_raw_af_table() -> None:
    con = memdb()
    try:
        db.upsert_rows(con, "players", "player_id", [], schema="raw_af")
    except ValueError as exc:
        assert "Unsupported raw table" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_normalize_name_strips_suffix_and_accents() -> None:
    assert normalize_name("Manchester City FC") == "manchester city"
    assert normalize_name("Real Sociedad") == "real sociedad"
    assert normalize_name("São Paulo") == "sao paulo"


def test_build_team_map_exact_override_unmapped() -> None:
    fd = [{"team_id": 65, "team_name": "Manchester City FC"},
          {"team_id": 57, "team_name": "Arsenal FC"},
          {"team_id": 999, "team_name": "Unknown Rovers"}]
    af = [{"team_id": 50, "team_name": "Manchester City"},
          {"team_id": 42, "team_name": "Arsenal"}]
    rows = build_team_map(fd, af, overrides={57: 9999})
    by_fd = {r["fd_team_id"]: r for r in rows}
    assert by_fd[65]["af_team_id"] == 50 and by_fd[65]["confidence"] == "exact"
    assert by_fd[57]["af_team_id"] == 9999 and by_fd[57]["confidence"] == "override"
    assert by_fd[999]["af_team_id"] is None and by_fd[999]["confidence"] == "unmapped"


def test_upsert_team_map_replaces() -> None:
    con = memdb()
    upsert_team_map(con, [{"fd_team_id": 65, "af_team_id": 50,
                           "team_name": "Manchester City FC", "confidence": "exact"}])
    upsert_team_map(con, [{"fd_team_id": 57, "af_team_id": 42,
                           "team_name": "Arsenal FC", "confidence": "exact"}])
    assert con.execute("SELECT COUNT(*) FROM metadata.team_map").fetchone()[0] == 1

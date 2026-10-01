"""Offline integration checks for the first milestone."""

from datetime import date
from pathlib import Path
from unittest.mock import Mock

import duckdb
import pytest

from ingestion.config import Config
from ingestion.ingest_standings import standing_rows
from ingestion.run_ingestion import ingest


def config(path: Path) -> Config:
    return Config("test-token", "https://example.test/v4", "PL", 2026, path)


def fake_client() -> Mock:
    client = Mock()
    client.get_competitions.return_value = {"competitions": [
        {"id": 2021, "name": "Premier League", "code": "PL", "type": "LEAGUE",
         "area": {"name": "England"}}]}
    client.get_teams.return_value = {"teams": [
        {"id": 1, "name": "Alpha", "area": {"name": "England"}},
        {"id": 2, "name": "Beta", "area": {"name": "England"}}]}
    client.get_matches.return_value = {"matches": [
        {"id": 42, "competition": {"id": 2021, "name": "Premier League"},
         "season": {"id": 900, "startDate": "2026-08-01", "endDate": "2027-05-31"},
         "utcDate": "2026-10-01T15:00:00Z", "status": "SCHEDULED",
         "homeTeam": {"id": 1, "name": "Alpha"},
         "awayTeam": {"id": 2, "name": "Beta"},
         "score": {"fullTime": {"home": None, "away": None}}}]}
    client.get_standings.return_value = {
        "competition": {"id": 2021}, "season": {"id": 900},
        "standings": [{"type": "TOTAL", "stage": "REGULAR_SEASON", "group": None,
                       "table": [
                           {"position": 1, "team": {"id": 1, "name": "Alpha"},
                            "playedGames": 0, "points": 0},
                           {"position": 2, "team": {"id": 2, "name": "Beta"},
                            "playedGames": 0, "points": 0},
                       ]}]}
    return client


def test_repeat_load_updates_without_duplicates(tmp_path: Path) -> None:
    db_path = tmp_path / "football.duckdb"
    client = fake_client()
    ingest(config(db_path), client, today=date(2026, 10, 1))
    match = client.get_matches.return_value["matches"][0]
    match["status"] = "FINISHED"
    match["score"]["fullTime"] = {"home": 2, "away": 1}
    ingest(config(db_path), client, today=date(2026, 10, 1))
    assert client.get_matches.call_args.kwargs == {
        "date_from": "2026-09-28", "date_to": "2026-10-09"}
    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT count(*) FROM raw.matches").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM raw.teams").fetchone()[0] == 2
        assert con.execute("SELECT count(*) FROM raw.standings").fetchone()[0] == 2
        assert con.execute("SELECT status, home_score FROM raw.matches").fetchone() == ("FINISHED", 2)
        assert con.execute("SELECT status, rows_inserted, rows_updated FROM metadata.pipeline_runs ORDER BY started_at DESC LIMIT 1").fetchone() == ("SUCCESS", 0, 6)


def test_forced_full_refresh_ignores_window(tmp_path: Path) -> None:
    db_path = tmp_path / "football.duckdb"
    client = fake_client()
    ingest(config(db_path), client, today=date(2026, 10, 1))
    forced = Config("test-token", "https://example.test/v4", "PL", 2026,
                    db_path, full_refresh=True)
    ingest(forced, client, today=date(2026, 10, 1))
    assert client.get_matches.call_args.kwargs == {}


def test_standing_types_have_distinct_keys() -> None:
    response = {
        "competition": {"id": 2021}, "season": {"id": 900},
        "standings": [
            {"type": standing_type, "stage": "REGULAR_SEASON", "group": None,
             "table": [{"team": {"id": 1, "name": "Alpha"},
                        "position": 1, "points": 3}]}
            for standing_type in ("TOTAL", "HOME", "AWAY")
        ],
    }
    rows = standing_rows(response, "batch", "PL", 2026)
    assert len(rows) == 3
    assert len({row["standing_key"] for row in rows}) == 3
    assert {row["standing_type"] for row in rows} == {"TOTAL", "HOME", "AWAY"}


def test_failed_api_call_records_failed_run(tmp_path: Path) -> None:
    db_path = tmp_path / "football.duckdb"
    client = fake_client()
    client.get_matches.side_effect = RuntimeError("API unavailable")
    with pytest.raises(RuntimeError, match="API unavailable"):
        ingest(config(db_path), client)
    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT status FROM metadata.pipeline_runs").fetchone()[0] == "FAILED"
        assert con.execute("SELECT count(*) FROM raw.matches").fetchone()[0] == 0

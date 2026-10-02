"""API-Football backfill with an injected fake client (no key, no network)."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from ingestion.api_football_client import QuotaExceeded
from ingestion.config import Config
from ingestion.run_af_backfill import backfill

FIXTURES_PAYLOAD = {"errors": [], "response": [
    {"fixture": {"id": 1, "date": "2026-08-16T14:00:00+00:00", "timestamp": 1,
                 "status": {"long": "Match Finished", "short": "FT", "elapsed": 90}},
     "league": {"id": 39, "name": "Premier League", "season": 2026,
                "round": "Regular Season - 1"},
     "teams": {"home": {"id": 50, "name": "Manchester City", "winner": True},
               "away": {"id": 42, "name": "Arsenal", "winner": False}},
     "goals": {"home": 2, "away": 0}},
    {"fixture": {"id": 2, "date": "2026-08-23T14:00:00+00:00", "timestamp": 2,
                 "status": {"long": "Not Started", "short": "NS", "elapsed": None}},
     "league": {"id": 39, "name": "Premier League", "season": 2026,
                "round": "Regular Season - 2"},
     "teams": {"home": {"id": 42, "name": "Arsenal", "winner": None},
               "away": {"id": 50, "name": "Manchester City", "winner": None}},
     "goals": {"home": None, "away": None}},
]}

EVENTS_PAYLOAD = {"errors": [], "response": [
    {"time": {"elapsed": 23, "extra": None},
     "team": {"id": 50, "name": "Manchester City"},
     "player": {"id": 617, "name": "E. Haaland"},
     "assist": {"id": None, "name": None},
     "type": "Goal", "detail": "Normal Goal", "comments": None},
]}


def make_config(tmp_path: Path) -> Config:
    return Config(api_token="x", api_base_url="http://x", competition="PL",
                  season=2026, duckdb_path=tmp_path / "test.duckdb",
                  api_football_key="test-key")


def make_client() -> Mock:
    client = Mock()
    client.get_fixtures.return_value = FIXTURES_PAYLOAD
    client.get_fixture_events.return_value = EVENTS_PAYLOAD
    return client


def test_backfill_loads_fixtures_and_finished_events(tmp_path: Path) -> None:
    import duckdb
    config = make_config(tmp_path)
    run_id = backfill(config, 39, 2026, max_events=5, client=make_client())
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM raw_af.fixtures").fetchone()[0] == 2
        # Only the finished fixture gets events; the NS one is skipped.
        assert con.execute("SELECT COUNT(*) FROM raw_af.events").fetchone()[0] == 1
        status = con.execute("SELECT status FROM metadata.pipeline_runs WHERE run_id = ?",
                             [run_id]).fetchone()[0]
        assert status == "SUCCESS"
        assert con.execute("SELECT calls FROM metadata.api_quota").fetchone()[0] == 2


def test_backfill_aborts_on_quota_and_records_failed_run(tmp_path: Path) -> None:
    import duckdb
    config = make_config(tmp_path)
    client = make_client()
    # First run spends its 2 calls.
    backfill(config, 39, 2026, max_events=5, client=client)
    with pytest.raises(QuotaExceeded):
        backfill(config, 39, 2026, max_events=100, client=client)
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert client.get_fixtures.call_count == 1  # second run never called the API
        failed = con.execute("SELECT COUNT(*) FROM metadata.pipeline_runs WHERE status = 'FAILED'").fetchone()[0]
        assert failed == 1


def test_backfill_requires_key(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config = Config(api_token="x", api_base_url="http://x", competition="PL",
                    season=2026, duckdb_path=config.duckdb_path, api_football_key="")
    with pytest.raises(ValueError, match="API_FOOTBALL_KEY"):
        backfill(config, 39, 2026, client=make_client())


def test_backfill_depth_loads_lineups_stats_players_odds(tmp_path: Path) -> None:
    import duckdb
    from tests.test_af_depth import LINEUPS, ODDS, PLAYERS, STATS
    config = make_config(tmp_path)
    client = make_client()
    client.get_lineups.return_value = {"errors": [], "response": LINEUPS}
    client.get_fixture_statistics.return_value = {"errors": [], "response": STATS}
    client.get_fixture_players.return_value = {"errors": [], "response": PLAYERS}
    client.get_odds.return_value = {"errors": [], "response": ODDS}
    backfill(config, 39, 2026, max_events=5, max_depth=2,
             include_odds=True, client=client)
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM raw_af.lineups").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM raw_af.fixture_stats").fetchone()[0] == 4
        assert con.execute("SELECT COUNT(*) FROM raw_af.player_stats").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM raw_af.odds").fetchone()[0] == 3
        # 1 fixtures + 1 events + 3 depth + 1 odds = 6 calls.
        assert con.execute("SELECT calls FROM metadata.api_quota").fetchone()[0] == 6


def test_backfill_without_depth_skips_depth_tables(tmp_path: Path) -> None:
    import duckdb
    config = make_config(tmp_path)
    backfill(config, 39, 2026, max_events=5, client=make_client())
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM raw_af.lineups").fetchone()[0] == 0


def test_backfill_injuries_costs_one_call(tmp_path: Path) -> None:
    import duckdb
    config = make_config(tmp_path)
    client = make_client()
    client.get_injuries.return_value = {"errors": [], "response": [{
        "player": {"id": 617, "name": "E. Haaland", "type": "Injury", "reason": "Knee"},
        "team": {"id": 50, "name": "Manchester City"},
        "fixture": {"id": 2, "date": "2026-08-23T14:00:00+00:00"}}]}
    backfill(config, 39, 2026, max_events=5, load_injuries=True, client=client)
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM raw_af.injuries").fetchone()[0] == 1
        # 1 fixtures + 1 events + 1 injuries = 3 calls.
        assert con.execute("SELECT calls FROM metadata.api_quota").fetchone()[0] == 3

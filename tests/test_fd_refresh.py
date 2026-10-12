"""Multi-competition football-data.org refresh (offline, mocked API)."""

import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import duckdb
import pytest
import requests

from ingestion import config as config_module
from ingestion import run_ingestion as ingest_module
from ingestion.api_client import FootballDataClient
from ingestion.config import Config
from ingestion.current_season import discover_season
from ingestion.run_ingestion import ingest_all, main


def comp_entry(code: str, name: str, start: str, season_id: int = 1) -> dict[str, Any]:
    return {"id": hash(code) % 10000, "code": code, "name": name, "type": "LEAGUE",
            "currentSeason": {"id": season_id, "startDate": start, "endDate": start[:4] + "-05-31"}}


def match_entry(match_id: int, code: str, status: str = "FINISHED",
                home: int = 3, away: int = 1) -> dict[str, Any]:
    return {"id": match_id, "utcDate": "2026-10-01T15:00:00Z", "status": status,
            "matchday": 1, "stage": "REGULAR_SEASON",
            "competition": {"id": 1, "name": code}, "season": {"id": 1},
            "homeTeam": {"id": 10, "name": "Alpha FC"},
            "awayTeam": {"id": 11, "name": "Beta FC"},
            "score": {"winner": "HOME_TEAM" if home is not None and home > (away or 0) else None,
                      "duration": "REGULAR", "fullTime": {"home": home, "away": away}}}


class FakeFDClient:
    """Two competitions; PD's teams endpoint is plan-locked (403)."""

    def __init__(self, fail_pd_teams: bool = True) -> None:
        self.fail_pd_teams = fail_pd_teams
        self.calls: list[str] = []

    def get_competitions(self) -> dict[str, Any]:
        self.calls.append("competitions")
        return {"competitions": [
            comp_entry("PL", "Premier League", "2026-08-21"),
            comp_entry("PD", "Primera Division", "2026-08-16"),
        ]}

    def get_teams(self, competition: str, season: int | None = None) -> dict[str, Any]:
        self.calls.append(f"teams:{competition}")
        if competition == "PD" and self.fail_pd_teams:
            raise RuntimeError("API HTTP 403 for /competitions/PD/teams")
        return {"teams": [
            {"id": 10, "name": "Alpha FC", "shortName": "Alpha", "tla": "ALP",
             "area": {"name": "X"}},
            {"id": 11, "name": "Beta FC", "shortName": "Beta", "tla": "BET",
             "area": {"name": "X"}}],
            "competition": {"id": 1}}

    def get_matches(self, competition: str, season: int | None = None, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(f"matches:{competition}")
        return {"matches": [match_entry(1000 + hash(competition) % 100, competition)]}

    def get_standings(self, competition: str, season: int | None = None, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(f"standings:{competition}")
        return {"competition": {"id": 1}, "season": {"id": 1}, "standings": []}


def make_config(tmp_path: Path, **overrides: Any) -> Config:
    base = dict(api_token="x", api_base_url="http://x", competition="PL",
                season=2026, duckdb_path=tmp_path / "test.duckdb",
                competitions=("PL", "PD"), api_pace_seconds=0)
    base.update(overrides)
    return Config(**base)  # type: ignore[arg-type]


def runs(con: duckdb.DuckDBPyConnection) -> list[tuple]:
    return con.execute(
        "SELECT pipeline_name, status FROM metadata.pipeline_runs ORDER BY started_at").fetchall()


def test_discover_season_from_metadata() -> None:
    assert discover_season([comp_entry("PD", "Primera", "2026-08-16")], "PD") == 2026


def test_discover_season_missing_competition() -> None:
    with pytest.raises(ValueError, match="absent from API"):
        discover_season([], "XX")


def test_discover_season_unparseable() -> None:
    bad = [{"code": "PD", "currentSeason": {"startDate": None}}]
    with pytest.raises(ValueError, match="pass FOOTBALL_SEASON explicitly"):
        discover_season(bad, "PD")


def test_config_competitions_and_auto_season(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    monkeypatch.setenv("FOOTBALL_API_TOKEN", "test")
    monkeypatch.setenv("FOOTBALL_COMPETITIONS", "pl, pd ,BL1")
    monkeypatch.setenv("FOOTBALL_SEASON", "auto")
    config = config_module.Config.from_env()
    assert config.competitions == ("PL", "PD", "BL1")
    assert config.competition == "PL"
    assert config.season is None


def test_config_rejects_bad_pace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    monkeypatch.setenv("FOOTBALL_API_TOKEN", "test")
    monkeypatch.setenv("FOOTBALL_API_PACE_SECONDS", "-1")
    with pytest.raises(ValueError, match="PACE"):
        config_module.Config.from_env()


def test_ingest_all_success_and_plan_locked_skip(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    summary = ingest_all(config, FakeFDClient(), today=datetime.date(2026, 10, 12))
    assert summary["PL"]["status"] == "SUCCESS"
    assert summary["PD"]["status"] == "SKIPPED"
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        statuses = [row[1] for row in runs(con)]
        assert "SUCCESS" in statuses and "SKIPPED" in statuses
        assert con.execute("SELECT COUNT(*) FROM raw.matches").fetchone()[0] == 1


def test_unknown_competition_skipped_without_api_spend(tmp_path: Path) -> None:
    config = make_config(tmp_path, competitions=("XX", "PL"), season=None)
    summary = ingest_all(config, FakeFDClient(fail_pd_teams=False),
                         today=datetime.date(2026, 10, 12))
    assert summary["XX"]["status"] == "SKIPPED"
    assert summary["PL"]["status"] == "SUCCESS"


def test_genuine_error_records_failed_and_main_exits_1(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config(tmp_path, competitions=("PL",))
    client = FakeFDClient(fail_pd_teams=False)
    client.get_matches = Mock(side_effect=RuntimeError("API HTTP 500 for /x"))
    monkeypatch.setattr(ingest_module, "FootballDataClient", Mock(return_value=client))
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    monkeypatch.setenv("FOOTBALL_API_TOKEN", "test")
    monkeypatch.setenv("FOOTBALL_COMPETITIONS", "PL")
    monkeypatch.setenv("FOOTBALL_SEASON", "2026")
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "test.duckdb"))
    monkeypatch.setenv("FOOTBALL_API_PACE_SECONDS", "0")
    assert main() == 1
    with duckdb.connect(str(tmp_path / "test.duckdb"), read_only=True) as con:
        assert runs(con)[0][1] == "FAILED"


def test_repeat_refresh_no_duplicates(tmp_path: Path) -> None:
    config = make_config(tmp_path, competitions=("PL",), full_refresh=True)
    client = FakeFDClient(fail_pd_teams=False)
    ingest_all(config, client, today=datetime.date(2026, 10, 12))
    ingest_all(config, client, today=datetime.date(2026, 10, 12))
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM raw.matches").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM raw.matches WHERE _competition='PL'").fetchone()[0] == 1


def test_postponed_match_null_scores_stored(tmp_path: Path) -> None:
    config = make_config(tmp_path, competitions=("PL",))
    client = FakeFDClient(fail_pd_teams=False)
    client.get_matches = Mock(return_value={"matches": [
        match_entry(2001, "PL", status="POSTPONED", home=None, away=None)]})
    ingest_all(config, client, today=datetime.date(2026, 10, 12))
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        row = con.execute(
            "SELECT status, home_score, away_score FROM raw.matches WHERE match_id=2001").fetchone()
        assert row == ("POSTPONED", None, None)


def test_fd_refresh_leaves_other_provider_tables_untouched(tmp_path: Path) -> None:
    config = make_config(tmp_path, competitions=("PL",))
    with duckdb.connect(str(config.duckdb_path)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw_af")
        con.execute("CREATE TABLE raw_af.fixtures (fixture_id INTEGER PRIMARY KEY)")
        con.execute("INSERT INTO raw_af.fixtures VALUES (9)")
    ingest_all(config, FakeFDClient(fail_pd_teams=False), today=datetime.date(2026, 10, 12))
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM raw_af.fixtures").fetchone()[0] == 1


def test_fd_client_retries_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("time.sleep", lambda *args: None)
    limited = Mock(status_code=429, headers={})
    ok = Mock(status_code=200, headers={}, json=lambda: {"competitions": []})
    session = requests.Session()
    session.get = Mock(side_effect=[limited, ok])
    assert FootballDataClient("t", session=session).get_competitions() == {"competitions": []}
    assert session.get.call_count == 2


def test_fd_client_paces_every_request() -> None:
    session = requests.Session()
    session.get = Mock(return_value=Mock(
        status_code=200, headers={}, json=lambda: {"competitions": []}))
    slept: list[float] = []
    import time as time_module
    real_sleep = time_module.sleep
    try:
        time_module.sleep = slept.append  # type: ignore[method-assign]
        FootballDataClient("t", session=session, pace_seconds=2.5).get_competitions()
    finally:
        time_module.sleep = real_sleep
    assert slept == [2.5]


def test_persistent_rate_limit_skips_without_losing_data(tmp_path: Path) -> None:
    config = make_config(tmp_path, competitions=("PL",))
    client = FakeFDClient(fail_pd_teams=False)
    client.get_matches = Mock(side_effect=RuntimeError("API HTTP 429 for /x"))
    summary = ingest_all(config, client, today=datetime.date(2026, 10, 12))
    assert summary["PL"]["status"] == "SKIPPED"
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        row = con.execute(
            "SELECT status FROM metadata.pipeline_runs").fetchone()
        assert row[0] == "SKIPPED"


def test_fd_client_auth_failure_fast_no_retry() -> None:
    session = requests.Session()
    response = Mock(status_code=401, headers={})
    response.raise_for_status.side_effect = requests.HTTPError("unauthorized")
    session.get = Mock(return_value=response)
    with pytest.raises(RuntimeError, match="API HTTP 401"):
        FootballDataClient("t", session=session).get_teams("PL", 2026)
    assert session.get.call_count == 1


def test_fd_client_timeout_is_wrapped() -> None:
    session = requests.Session()
    session.get = Mock(side_effect=requests.Timeout("slow"))
    with pytest.raises(RuntimeError, match="API request failed"):
        FootballDataClient("t", session=session, max_retries=0).get_standings("PL", 2026)

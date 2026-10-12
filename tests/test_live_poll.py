"""Live poller with an injected fake client (no key, no network)."""

from datetime import date
from pathlib import Path
from unittest.mock import Mock

import duckdb
import pytest

from ingestion import config as config_module
from ingestion import run_live_poll as poll_module
from ingestion.api_football_client import QuotaExceeded
from ingestion.config import Config
from ingestion.run_live_poll import NoAccessibleSeason, default_season, main, poll


def fixture(fixture_id: int, short: str, date: str = "2026-10-03T15:00:00+00:00") -> dict:
    long = {"1H": "First Half", "NS": "Not Started", "FT": "Match Finished"}.get(short, short)
    elapsed = 33 if short == "1H" else (90 if short == "FT" else None)
    goals = {"home": 1, "away": 0} if short in {"1H", "FT"} else {"home": None, "away": None}
    return {
        "fixture": {"id": fixture_id, "date": date, "timestamp": fixture_id,
                    "status": {"long": long, "short": short, "elapsed": elapsed}},
        "league": {"id": 39, "name": "Premier League", "season": 2026, "round": "R1"},
        "teams": {"home": {"id": 50, "name": "Manchester City", "winner": None},
                  "away": {"id": 42, "name": "Arsenal", "winner": None}},
        "goals": goals,
    }


EVENT = {"time": {"elapsed": 23, "extra": None},
         "team": {"id": 50, "name": "Manchester City"},
         "player": {"id": 617, "name": "E. Haaland"},
         "assist": {"id": None, "name": None},
         "type": "Goal", "detail": "Normal Goal", "comments": None}


def make_config(tmp_path: Path, abort_at: int = 90) -> Config:
    return Config(api_token="x", api_base_url="http://x", competition="PL",
                  season=2026, duckdb_path=tmp_path / "test.duckdb",
                  api_football_key="test-key", api_football_abort_at=abort_at)


def make_client(fixtures: list[dict]) -> Mock:
    client = Mock()
    client.get_fixtures.return_value = {"errors": [], "response": fixtures}
    client.get_fixture_events.return_value = {"errors": [], "response": [EVENT]}
    return client


def read(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None):
    return con.execute(sql, params or []).fetchone()[0]


def test_idle_day_costs_one_call(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    run_id = poll(config, 39, client=make_client([fixture(1, "NS")]), today="2026-10-03")
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert read(con, "SELECT COUNT(*) FROM raw_af.fixtures") == 1
        assert read(con, "SELECT COUNT(*) FROM raw_af.events") == 0
        assert read(con, "SELECT calls FROM metadata.api_quota") == 1
        assert read(con, "SELECT status FROM metadata.pipeline_runs WHERE run_id = ?",
                    [run_id]) == "SUCCESS"


def test_live_fixture_events_refreshed(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    client = make_client([fixture(1, "1H"), fixture(2, "NS")])
    poll(config, 39, client=client, today="2026-10-03")
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert read(con, "SELECT COUNT(*) FROM raw_af.events") == 1
        assert read(con, "SELECT calls FROM metadata.api_quota") == 2
    assert client.get_fixture_events.call_count == 1


def test_finished_fixture_backfilled(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    poll(config, 39, client=make_client([fixture(1, "FT")]), today="2026-10-03")
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        assert read(con, "SELECT COUNT(*) FROM raw_af.events") == 1
        assert read(con, "SELECT calls FROM metadata.api_quota") == 2


def test_quota_abort_spends_nothing(tmp_path: Path) -> None:
    config = make_config(tmp_path, abort_at=2)
    client = make_client([fixture(1, "1H")])
    poll(config, 39, client=client, today="2026-10-03")
    with pytest.raises(QuotaExceeded):
        poll(config, 39, max_live=100, client=client, today="2026-10-03")
    assert client.get_fixtures.call_count == 1  # aborted before any new call


def test_goal_between_polls_sends_notification(tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types
    from unittest.mock import Mock

    from api.push_store import subscribe

    config = make_config(tmp_path)
    one = dict(fixture(1, "1H"))
    one["goals"] = {"home": 1, "away": 0}
    two = dict(fixture(1, "1H"))
    two["goals"] = {"home": 2, "away": 0}
    client = make_client([one])
    poll(config, 39, client=client, today="2026-10-03")

    import duckdb
    with duckdb.connect(str(config.duckdb_path)) as con:
        subscribe(con, "https://push/a", "p", "a")

    module = types.ModuleType("pywebpush")
    module.WebPushException = type("Gone", (Exception,), {})  # type: ignore[attr-defined]
    sender = Mock()
    module.webpush = sender  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pywebpush", module)
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-key")

    client.get_fixtures.return_value = {"errors": [], "response": [two]}
    poll(config, 39, client=client, today="2026-10-03")
    assert sender.call_count == 1
    assert "Manchester City 2" in sender.call_args.args[1]


def test_default_season_follows_football_calendar() -> None:
    assert default_season(date(2026, 10, 12)) == 2026
    assert default_season(date(2026, 7, 1)) == 2026
    assert default_season(date(2026, 3, 1)) == 2025


def test_season_passed_to_fixtures_call(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    client = make_client([fixture(1, "NS")])
    poll(config, 39, season=2024, client=client, today="2026-10-03")
    assert client.get_fixtures.call_args.kwargs == {
        "league": 39, "season": 2024, "date_": "2026-10-03"}


def test_plan_error_records_skipped_run(tmp_path: Path) -> None:
    import duckdb
    config = make_config(tmp_path)
    client = make_client([])
    client.get_fixtures.side_effect = ValueError(
        "API-Football errors on /fixtures: {'season': 'The Season field is required.'}")
    with pytest.raises(NoAccessibleSeason, match="not accessible"):
        poll(config, 39, client=client, today="2026-10-03")
    with duckdb.connect(str(config.duckdb_path), read_only=True) as con:
        row = con.execute(
            "SELECT status, error_message FROM metadata.pipeline_runs").fetchone()
        assert row[0] == "SKIPPED"
        assert "not accessible" in (row[1] or "")


def test_main_returns_zero_on_skipped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config_module, "load_dotenv", lambda: None)
    monkeypatch.setenv("FOOTBALL_API_TOKEN", "test")
    monkeypatch.setenv("API_FOOTBALL_KEY", "test")
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "test.duckdb"))
    monkeypatch.setattr(poll_module, "poll",
                        Mock(side_effect=NoAccessibleSeason("plan locked")))
    assert main(["--league", "39"]) == 0

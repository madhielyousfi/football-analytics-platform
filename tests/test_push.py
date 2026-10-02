"""Push subscriptions and goal-change detection (no network, no VAPID send)."""

import sys
import types
from unittest.mock import Mock

import duckdb
import pytest

from api.push_store import (
    all_subscriptions,
    detect_goal_changes,
    score_snapshot,
    send_goal_notifications,
    subscribe,
    unsubscribe,
)


def memdb() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


def test_subscribe_upsert_and_unsubscribe() -> None:
    con = memdb()
    subscribe(con, "https://push/a", "p256-a", "auth-a", label="fan phone")
    subscribe(con, "https://push/a", "p256-b", "auth-b", label="fan phone")
    subs = all_subscriptions(con)
    assert len(subs) == 1 and subs[0]["p256dh"] == "p256-b"
    assert unsubscribe(con, "https://push/a") == 1
    assert unsubscribe(con, "https://push/a") == 0
    assert all_subscriptions(con) == []


def after_row(fid: int, home: int | None, away: int | None,
              status: str = "1H", elapsed: int | None = 33) -> dict:
    return {"fixture_id": fid, "home_team_name": "Manchester City",
            "away_team_name": "Arsenal", "goals_home": home,
            "goals_away": away, "status_short": status, "elapsed": elapsed}


def test_goal_growth_detected_once() -> None:
    before = {1: (1, 0), 2: (0, 0)}
    notes = detect_goal_changes(before, [after_row(1, 2, 0), after_row(2, 0, 0)])
    assert len(notes) == 1
    assert notes[0]["fixture_id"] == 1
    assert "Manchester City 2–0 Arsenal" in notes[0]["title"]


def test_no_note_for_new_scoreless_or_scheduled() -> None:
    before: dict = {}
    rows = [after_row(9, 0, 0, status="NS", elapsed=None),
            after_row(9, None, None, status="1H")]
    assert detect_goal_changes(before, rows) == []
    assert detect_goal_changes({9: (0, 0)}, [after_row(9, 0, 0)]) == []


def stub_pywebpush(monkeypatch: pytest.MonkeyPatch, behavior: str) -> Mock:
    """Inject a fake pywebpush module: 'ok' sends, 'gone' raises 410."""
    module = types.ModuleType("pywebpush")

    class Gone(Exception):
        def __init__(self) -> None:
            self.response = Mock(status_code=410)

    module.WebPushException = Gone  # type: ignore[attr-defined]
    sender = Mock()
    if behavior == "gone":
        sender.side_effect = Gone()
    module.webpush = sender  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pywebpush", module)
    return sender


def test_send_skipped_without_vapid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    con = memdb()
    subscribe(con, "https://push/a", "p", "a")
    notes = [{"fixture_id": 1, "title": "t", "body": "b"}]
    assert send_goal_notifications(con, notes) == 0
    assert send_goal_notifications(con, []) == 0


def test_send_delivers_and_drops_dead_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-key")
    con = memdb()
    subscribe(con, "https://push/a", "p", "a")
    notes = [{"fixture_id": 1, "title": "t", "body": "b"}]
    sender = stub_pywebpush(monkeypatch, "ok")
    assert send_goal_notifications(con, notes) == 1
    assert sender.call_count == 1
    payload = sender.call_args.args[1]
    assert "fixture/1" in payload

    stub_pywebpush(monkeypatch, "gone")
    assert send_goal_notifications(con, notes) == 0
    assert all_subscriptions(con) == []


def test_score_snapshot_empty_on_fresh_db() -> None:
    assert score_snapshot(memdb(), 39) == {}

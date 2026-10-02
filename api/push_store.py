"""Web Push subscription store + goal-change detection (DuckDB-backed)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import duckdb

LOGGER = logging.getLogger(__name__)


def ensure_push_tables(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS metadata")
    connection.execute("""CREATE TABLE IF NOT EXISTS metadata.push_subscriptions (
        endpoint VARCHAR PRIMARY KEY, p256dh VARCHAR NOT NULL, auth VARCHAR NOT NULL,
        label VARCHAR, created_at TIMESTAMPTZ NOT NULL
    )""")


def subscribe(connection: duckdb.DuckDBPyConnection, endpoint: str,
              p256dh: str, auth: str, label: str | None = None) -> None:
    """Insert or refresh a push subscription."""
    ensure_push_tables(connection)
    connection.execute(
        """INSERT INTO metadata.push_subscriptions
           (endpoint, p256dh, auth, label, created_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (endpoint) DO UPDATE SET
             p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth,
             label = EXCLUDED.label, created_at = EXCLUDED.created_at""",
        [endpoint, p256dh, auth, label, datetime.now(timezone.utc)])


def unsubscribe(connection: duckdb.DuckDBPyConnection, endpoint: str) -> int:
    """Remove a subscription; returns rows deleted (0 or 1)."""
    ensure_push_tables(connection)
    return len(connection.execute(
        "DELETE FROM metadata.push_subscriptions WHERE endpoint = ? RETURNING endpoint",
        [endpoint]).fetchall())


def all_subscriptions(connection: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    ensure_push_tables(connection)
    cols = ["endpoint", "p256dh", "auth", "label"]
    return [dict(zip(cols, row)) for row in
            connection.execute("SELECT endpoint, p256dh, auth, label "
                               "FROM metadata.push_subscriptions").fetchall()]


def score_snapshot(connection: duckdb.DuckDBPyConnection,
                   league_id: int) -> dict[int, tuple[int | None, int | None]]:
    """Current (goals_home, goals_away) per fixture for goal-change diffing."""
    try:
        rows = connection.execute(
            "SELECT fixture_id, goals_home, goals_away FROM raw_af.fixtures"
            " WHERE league_id = ?", [league_id]).fetchall()
    except duckdb.CatalogException:
        return {}
    return {r[0]: (r[1], r[2]) for r in rows}


def detect_goal_changes(before: dict[int, tuple[int | None, int | None]],
                        after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare score snapshots; return a notification per fixture whose total grew.

    `before`: fixture_id -> (goals_home, goals_away). `after`: fresh fixture
    rows with keys fixture_id/home_team_name/away_team_name/goals_home/
    goals_away/status_short/elapsed.
    """
    notes = []
    for row in after:
        fid = row["fixture_id"]
        old = before.get(fid)
        if old is None:
            continue
        old_home, old_away = old
        new_home, new_away = row.get("goals_home"), row.get("goals_away")
        if new_home is None or new_away is None:
            continue
        grew = ((old_home is not None and new_home > old_home)
                or (old_away is not None and new_away > old_away))
        if grew and (row.get("status_short") or "") != "NS":
            minute = f" · {row.get('elapsed')}′" if row.get("elapsed") is not None else ""
            notes.append({
                "fixture_id": fid,
                "title": f"⚽ Goal! {row['home_team_name']} {new_home}–{new_away} {row['away_team_name']}",
                "body": f"{row.get('status_short', '')}{minute}",
            })
    return notes


def send_goal_notifications(connection: duckdb.DuckDBPyConnection,
                            notes: list[dict[str, Any]],
                            base_url: str | None = None) -> int:
    """Deliver goal notes to all subscribers; drops dead endpoints.

    Returns messages sent. Skips silently when VAPID is unconfigured.
    """
    if not notes:
        return 0
    private_key = os.getenv("VAPID_PRIVATE_KEY", "").strip()
    subject = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com").strip()
    if not private_key:
        LOGGER.info("VAPID_PRIVATE_KEY unset; skipping %s push notifications", len(notes))
        return 0
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        LOGGER.warning("pywebpush not installed; skipping push notifications")
        return 0
    base = (base_url or os.getenv("APP_BASE_URL", "http://localhost:3000")).rstrip("/")
    subs = all_subscriptions(connection)
    sent = 0
    for sub in subs:
        info = {"endpoint": sub["endpoint"],
                "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}}
        for note in notes:
            payload = json.dumps({
                "title": note["title"], "body": note["body"],
                "url": f"{base}/fixture/{note['fixture_id']}",
            })
            try:
                webpush(info, payload,
                        vapid_private_key=private_key,
                        vapid_claims={"sub": subject})
                sent += 1
            except WebPushException as exc:
                status = getattr(exc.response, "status_code", None)
                if status in (404, 410):
                    unsubscribe(connection, sub["endpoint"])
                    LOGGER.info("Dropped dead push endpoint")
                else:
                    LOGGER.warning("Push failed: %s", exc)
                break
    return sent

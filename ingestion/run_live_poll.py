"""Poll today's league fixtures; fetch events only while it matters.

One cheap call (/fixtures?league&date) decides the run:
- nothing live and no finished fixture missing events -> exit (~1 call)
- live fixtures -> refresh their events (1 call each, capped)
- finished fixtures missing events -> backfill them (1 call each, capped)

Usage:
    python -m ingestion.run_live_poll --league 39 --max-live 6 --max-backfill 6
Requires API_FOOTBALL_KEY in .env. QuotaExceeded exits 0 after recording a
FAILED run (expected operational state on a schedule, not a code failure).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from uuid import uuid4

from ingestion.api_football_client import (
    ApiFootballClient,
    QuotaExceeded,
    check_daily_quota,
    record_call,
)
from api.push_store import (
    detect_goal_changes,
    score_snapshot,
    send_goal_notifications,
)
from ingestion.config import Config
from ingestion.database import (
    connect,
    create_tables,
    finish_run,
    start_run,
    upsert_rows,
)
from ingestion.ingest_af_fixtures import event_rows, fixture_rows

LOGGER = logging.getLogger(__name__)

LIVE_SHORT = {"1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE"}
DONE_SHORT = {"FT", "AET", "PEN"}


def _short(item: dict) -> str | None:
    return ((item.get("fixture") or {}).get("status") or {}).get("short")


def poll(config: Config, league_id: int, max_live: int = 6,
         max_backfill: int = 6,
         client: ApiFootballClient | None = None,
         today: str | None = None) -> str:
    """Run one poll cycle; returns run_id."""
    if not config.api_football_key:
        raise ValueError("API_FOOTBALL_KEY is required; set it in .env")
    client = client or ApiFootballClient(config.api_football_key,
                                         config.api_football_base_url)
    day = today or datetime.now(timezone.utc).date().isoformat()
    run_id = str(uuid4())
    LOGGER.info("Live poll: league=%s date=%s", league_id, day)
    with connect(config.duckdb_path) as connection:
        create_tables(connection)
        start_run(connection, run_id, pipeline="live_poll")
        received = inserted = updated = 0
        transaction_open = False
        try:
            check_daily_quota(connection, needed=1,
                              daily_limit=config.api_football_daily_limit,
                              abort_at=config.api_football_abort_at)
            payload = client.get_fixtures(league=league_id, date_=day)
            record_call(connection)
            items = payload.get("response", [])
            if not isinstance(items, list):
                raise ValueError("Invalid fixtures list in API response")
            LOGGER.info("Today's fixtures: %s", len(items))
            before = score_snapshot(connection, league_id)
            connection.execute("BEGIN TRANSACTION")
            transaction_open = True
            rows = fixture_rows(items, run_id)
            new, changed = upsert_rows(connection, "fixtures", "fixture_id",
                                       rows, schema="raw_af")
            received += len(rows)
            inserted += new
            updated += changed
            live_ids = [i["fixture"]["id"] for i in items
                        if _short(i) in LIVE_SHORT][:max_live]
            LOGGER.info("Live now: %s", len(live_ids))
            for fixture_id in live_ids:
                check_daily_quota(connection, needed=1,
                                  daily_limit=config.api_football_daily_limit,
                                  abort_at=config.api_football_abort_at)
                events = client.get_fixture_events(fixture_id).get("response", [])
                record_call(connection)
                if not isinstance(events, list):
                    raise ValueError(f"Invalid events list for fixture {fixture_id}")
                erows = event_rows(fixture_id, events, run_id)
                new, changed = upsert_rows(connection, "events", "event_key",
                                           erows, schema="raw_af")
                received += len(erows)
                inserted += new
                updated += changed
            missing = [r[0] for r in connection.execute(
                """SELECT f.fixture_id FROM raw_af.fixtures f
                   LEFT JOIN (SELECT DISTINCT fixture_id FROM raw_af.events) e
                     ON f.fixture_id = e.fixture_id
                   WHERE e.fixture_id IS NULL AND f.status_short IN ('FT', 'AET', 'PEN')
                     AND f.league_id = ?
                   ORDER BY f.fixture_date DESC LIMIT ?""",
                [league_id, max_backfill]).fetchall()]
            LOGGER.info("Finished without events: %s", len(missing))
            for fixture_id in missing:
                check_daily_quota(connection, needed=1,
                                  daily_limit=config.api_football_daily_limit,
                                  abort_at=config.api_football_abort_at)
                events = client.get_fixture_events(fixture_id).get("response", [])
                record_call(connection)
                if not isinstance(events, list):
                    raise ValueError(f"Invalid events list for fixture {fixture_id}")
                erows = event_rows(fixture_id, events, run_id)
                new, changed = upsert_rows(connection, "events", "event_key",
                                           erows, schema="raw_af")
                received += len(erows)
                inserted += new
                updated += changed
            connection.execute("COMMIT")
            transaction_open = False
            fresh = [dict(zip(
                ["fixture_id", "home_team_name", "away_team_name", "goals_home",
                 "goals_away", "status_short", "elapsed"],
                r)) for r in connection.execute(
                """SELECT fixture_id, home_team_name, away_team_name,
                   goals_home, goals_away, status_short, elapsed
                   FROM raw_af.fixtures WHERE league_id = ?""", [league_id]).fetchall()]
            sent = send_goal_notifications(connection, detect_goal_changes(before, fresh))
            if sent:
                LOGGER.info("Goal notifications sent: %s", sent)
            finish_run(connection, run_id, "SUCCESS", received, inserted, updated)
            LOGGER.info("Poll completed: run_id=%s", run_id)
        except Exception as exc:
            if transaction_open:
                connection.execute("ROLLBACK")
            finish_run(connection, run_id, "FAILED", received, 0, 0, str(exc))
            if isinstance(exc, QuotaExceeded):
                LOGGER.error("Poll stopped on quota: %s", exc)
            else:
                LOGGER.exception("Poll failed: run_id=%s", run_id)
            raise
    return run_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", type=int, default=39)
    parser.add_argument("--max-live", type=int, default=6)
    parser.add_argument("--max-backfill", type=int, default=6)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        poll(Config.from_env(), args.league, args.max_live, args.max_backfill)
        return 0
    except QuotaExceeded as exc:
        LOGGER.error("Quota exhausted, will retry next window: %s", exc)
        return 0
    except Exception as exc:
        LOGGER.error("Poll stopped: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

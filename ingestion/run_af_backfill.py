"""Backfill API-Football fixtures + events into raw_af tables.

Quota-aware: checks metadata.api_quota before spending. Fetches the fixture
list (1 call), then events only for finished fixtures missing them, newest
first, capped by max_events (each costs 1 call).

Usage:
    python -m ingestion.run_af_backfill --league 39 --season 2026 --max-events 10
Requires API_FOOTBALL_KEY in .env.
"""

from __future__ import annotations

import argparse
import logging
import sys
from uuid import uuid4

from ingestion.api_football_client import (
    ApiFootballClient,
    QuotaExceeded,
    check_daily_quota,
    record_call,
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

FINISHED = {"FT", "AET", "PEN"}


def backfill(config: Config, league_id: int, season: int,
             max_events: int = 10,
             client: ApiFootballClient | None = None) -> str:
    """Fetch fixtures + capped events; returns run_id. Raises QuotaExceeded."""
    if not config.api_football_key:
        raise ValueError("API_FOOTBALL_KEY is required; set it in .env")
    client = client or ApiFootballClient(config.api_football_key,
                                         config.api_football_base_url)
    run_id = str(uuid4())
    LOGGER.info("Starting API-Football backfill: league=%s season=%s", league_id, season)
    with connect(config.duckdb_path) as connection:
        create_tables(connection)
        start_run(connection, run_id, pipeline="af_backfill")
        received = inserted = updated = 0
        transaction_open = False
        try:
            check_daily_quota(connection, needed=1 + max_events,
                              daily_limit=config.api_football_daily_limit,
                              abort_at=config.api_football_abort_at)
            payload = client.get_fixtures(league=league_id, season=season)
            record_call(connection)
            items = payload.get("response", [])
            if not isinstance(items, list):
                raise ValueError("Invalid fixtures list in API response")
            LOGGER.info("Fixtures received: %s", len(items))
            connection.execute("BEGIN TRANSACTION")
            transaction_open = True
            rows = fixture_rows(items, run_id)
            new, changed = upsert_rows(connection, "fixtures", "fixture_id",
                                       rows, schema="raw_af")
            received += len(rows)
            inserted += new
            updated += changed
            # Events for finished fixtures missing them, newest first.
            missing = [r[0] for r in connection.execute(
                """SELECT f.fixture_id FROM raw_af.fixtures f
                   LEFT JOIN (SELECT DISTINCT fixture_id FROM raw_af.events) e
                     ON f.fixture_id = e.fixture_id
                   WHERE e.fixture_id IS NULL AND f.status_short IN ('FT', 'AET', 'PEN')
                   ORDER BY f.fixture_date DESC LIMIT ?""", [max_events]).fetchall()]
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
                LOGGER.info("Fixture %s events: new=%s updated=%s", fixture_id, new, changed)
            connection.execute("COMMIT")
            transaction_open = False
            finish_run(connection, run_id, "SUCCESS", received, inserted, updated)
            LOGGER.info("Backfill completed: run_id=%s", run_id)
        except Exception as exc:
            if transaction_open:
                connection.execute("ROLLBACK")
            status = "FAILED"
            if isinstance(exc, QuotaExceeded):
                LOGGER.error("Backfill stopped: %s", exc)
            else:
                LOGGER.exception("Backfill failed: run_id=%s", run_id)
            finish_run(connection, run_id, status, received, 0, 0, str(exc))
            raise
    return run_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", type=int, default=39)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--max-events", type=int, default=10)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        config = Config.from_env()
        backfill(config, args.league, args.season, args.max_events)
        return 0
    except Exception as exc:
        LOGGER.error("Backfill stopped: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

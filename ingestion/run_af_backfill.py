"""Backfill API-Football fixtures + events into raw_af tables.

Quota-aware: checks metadata.api_quota before spending. Fetches the fixture
list (1 call), then events only for finished fixtures missing them, newest
first, capped by max_events (each costs 1 call).

Usage:
    python -m ingestion.run_af_backfill --league 39 --season 2026 --max-events 10
    python -m ingestion.run_af_backfill --league 39 --season 2026 --max-depth 3 --include-odds
Requires API_FOOTBALL_KEY in .env. Depth costs ~3 calls/fixture (+1 odds).
Pacing (--pace-seconds, default 6) keeps the free plan's per-minute cap happy.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
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
from ingestion.ingest_af_depth import (
    fixture_stat_rows,
    injury_rows,
    lineup_rows,
    odd_rows,
    player_stat_rows,
)
from ingestion.ingest_af_fixtures import event_rows, fixture_rows

LOGGER = logging.getLogger(__name__)

FINISHED = {"FT", "AET", "PEN"}


def _load_depth(connection, client: ApiFootballClient, config: Config,
                run_id: str, fixture_id: int, include_odds: bool,
                received: int, inserted: int, updated: int,
                pace_seconds: float = 0) -> tuple[int, int, int]:
    """Fetch lineups, stats, players (+odds) for one fixture with quota checks."""
    for table, key, fetch, build in (
        ("lineups", "lineup_key", client.get_lineups,
         lambda items: lineup_rows(fixture_id, items, run_id)),
        ("fixture_stats", "stat_key", client.get_fixture_statistics,
         lambda items: fixture_stat_rows(fixture_id, items, run_id)),
        ("player_stats", "pstat_key", client.get_fixture_players,
         lambda items: player_stat_rows(fixture_id, items, run_id)),
    ):
        check_daily_quota(connection, needed=1,
                          daily_limit=config.api_football_daily_limit,
                          abort_at=config.api_football_abort_at)
        if pace_seconds > 0:
            time.sleep(pace_seconds)
        payload = fetch(fixture_id)
        record_call(connection)
        items = payload.get("response", [])
        if not isinstance(items, list):
            raise ValueError(f"Invalid {table} list for fixture {fixture_id}")
        rows = build(items)
        new, changed = upsert_rows(connection, table, key, rows, schema="raw_af")
        received += len(rows)
        inserted += new
        updated += changed
    if include_odds:
        check_daily_quota(connection, needed=1,
                          daily_limit=config.api_football_daily_limit,
                          abort_at=config.api_football_abort_at)
        if pace_seconds > 0:
            time.sleep(pace_seconds)
        payload = client.get_odds(fixture_id=fixture_id)
        record_call(connection)
        items = payload.get("response", [])
        if not isinstance(items, list):
            raise ValueError(f"Invalid odds list for fixture {fixture_id}")
        rows = odd_rows(fixture_id, items, run_id)
        new, changed = upsert_rows(connection, "odds", "odd_key", rows, schema="raw_af")
        received += len(rows)
        inserted += new
        updated += changed
    LOGGER.info("Fixture %s depth loaded (odds=%s)", fixture_id, include_odds)
    return received, inserted, updated


def backfill(config: Config, league_id: int, season: int,
             max_events: int = 10, max_depth: int = 0,
             include_odds: bool = False, load_injuries: bool = False,
             pace_seconds: float = 0,
             client: ApiFootballClient | None = None) -> str:
    """Fetch fixtures + capped events (+ optional depth/injuries). Returns run_id.

    Depth (lineups, stats, players, +odds) costs ~3-4 calls per fixture.
    Injuries cost 1 call for the whole league/season.
    """
    if not config.api_football_key:
        raise ValueError("API_FOOTBALL_KEY is required; set it in .env")
    client = client or ApiFootballClient(config.api_football_key,
                                         config.api_football_base_url)
    run_id = str(uuid4())
    LOGGER.info("Starting API-Football backfill: league=%s season=%s", league_id, season)

    def pace() -> None:
        if pace_seconds > 0:
            time.sleep(pace_seconds)
    with connect(config.duckdb_path) as connection:
        create_tables(connection)
        start_run(connection, run_id, pipeline="af_backfill")
        received = inserted = updated = 0
        transaction_open = False
        try:
            depth_calls = max_depth * (4 if include_odds else 3) if max_depth else 0
            check_daily_quota(connection, needed=1 + max_events + depth_calls + int(load_injuries),
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
                pace()
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
            if max_depth:
                deep = [r[0] for r in connection.execute(
                    """SELECT f.fixture_id FROM raw_af.fixtures f
                       LEFT JOIN (SELECT DISTINCT fixture_id FROM raw_af.lineups) l
                         ON f.fixture_id = l.fixture_id
                       WHERE l.fixture_id IS NULL AND f.status_short IN ('FT', 'AET', 'PEN')
                       ORDER BY f.fixture_date DESC LIMIT ?""", [max_depth]).fetchall()]
                LOGGER.info("Fixtures missing depth: %s", len(deep))
                for fixture_id in deep:
                    received, inserted, updated = _load_depth(
                        connection, client, config, run_id, fixture_id, include_odds,
                        received, inserted, updated, pace_seconds)
            if load_injuries:
                check_daily_quota(connection, needed=1,
                                  daily_limit=config.api_football_daily_limit,
                                  abort_at=config.api_football_abort_at)
                pace()
                injuries = client.get_injuries(league_id, season).get("response", [])
                record_call(connection)
                if not isinstance(injuries, list):
                    raise ValueError("Invalid injuries list in API response")
                irows = injury_rows(injuries, run_id)
                new, changed = upsert_rows(connection, "injuries", "injury_key",
                                           irows, schema="raw_af")
                received += len(irows)
                inserted += new
                updated += changed
                LOGGER.info("Injuries: new=%s updated=%s", new, changed)
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
    parser.add_argument("--max-depth", type=int, default=0)
    parser.add_argument("--include-odds", action="store_true")
    parser.add_argument("--load-injuries", action="store_true")
    parser.add_argument("--pace-seconds", type=float, default=6.0)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        config = Config.from_env()
        backfill(config, args.league, args.season, args.max_events,
                 args.max_depth, args.include_odds, args.load_injuries,
                 args.pace_seconds)
        return 0
    except Exception as exc:
        LOGGER.error("Backfill stopped: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

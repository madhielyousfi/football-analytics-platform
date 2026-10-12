"""Run full or rolling-window ingestion into DuckDB raw tables."""

from datetime import date, datetime, timedelta, timezone
import dataclasses
import logging
import sys
import time
from uuid import uuid4

from ingestion.api_client import FootballDataClient
from ingestion.config import Config
from ingestion.current_season import discover_season
from ingestion.database import (
    connect,
    create_tables,
    finish_run,
    mark_skipped,
    start_run,
    upsert_rows,
)
from ingestion.ingest_competitions import competition_rows
from ingestion.ingest_matches import match_rows
from ingestion.ingest_standings import standing_rows
from ingestion.ingest_teams import team_rows

LOGGER = logging.getLogger(__name__)

SKIP_HTTP = ("HTTP 404", "HTTP 403", "HTTP 429")


def ingest(config: Config, client: FootballDataClient | None = None,
           today: date | None = None, run_id: str | None = None) -> str:
    """Fetch source data and commit all raw tables as one batch."""
    client = client or FootballDataClient(config.api_token, config.api_base_url,
                                          config.api_timeout, config.api_max_retries,
                                          config.api_pace_seconds)
    run_id = run_id or str(uuid4())
    LOGGER.info("Starting football ingestion: competition=%s season=%s", config.competition, config.season)
    with connect(config.duckdb_path) as connection:
        create_tables(connection)
        start_run(connection, run_id)
        received = inserted = updated = 0
        transaction_open = False
        try:
            competitions = client.get_competitions().get("competitions", [])
            if not isinstance(competitions, list):
                raise ValueError("Invalid competitions list in API response")
            teams_response = client.get_teams(config.competition, config.season)
            teams = teams_response.get("teams", [])
            if not isinstance(teams, list):
                raise ValueError("Invalid teams list in API response")
            selected = next((item for item in competitions if item.get("code") == config.competition), None)
            if selected is None:
                selected = teams_response.get("competition")
            if not selected or selected.get("id") is None:
                raise ValueError(f"Competition {config.competition} absent from API response")
            existing_matches = connection.execute("""SELECT count(*) FROM raw.matches
                WHERE _competition = ? AND _season = ?""",
                [config.competition, config.season]).fetchone()[0]
            if existing_matches and not config.full_refresh:
                current_date = today or datetime.now(timezone.utc).date()
                date_from = current_date - timedelta(days=config.refresh_days_back)
                # The API's dateTo is exclusive; add one day to include the configured end date.
                date_to = current_date + timedelta(days=config.refresh_days_forward + 1)
                LOGGER.info("Refreshing match window: %s through %s UTC", date_from,
                            date_to - timedelta(days=1))
                matches_response = client.get_matches(
                    config.competition, config.season,
                    date_from=date_from.isoformat(), date_to=date_to.isoformat(),
                )
            else:
                LOGGER.info("Loading full season matches")
                matches_response = client.get_matches(config.competition, config.season)
            matches = matches_response.get("matches", [])
            if selected.get("type") in {"CUP", "PLAYOFFS"}:
                LOGGER.info("Attempting standings for %s competition (may be empty)",
                            selected.get("type"))
            try:
                standings_response = client.get_standings(config.competition, config.season)
            except Exception as exc:
                LOGGER.warning("Standings unavailable, continuing without them: %s", exc)
                standings_response = {"competition": selected, "standings": []}
            standings = standing_rows(standings_response, run_id,
                                      config.competition, config.season)
            for label, items in (("competitions", competitions), ("teams", teams),
                                 ("matches", matches), ("standings", standings)):
                if not isinstance(items, list):
                    raise ValueError(f"Invalid {label} list in API response")
                LOGGER.info("%s received: %s", label.capitalize(), len(items))
                if not items:
                    if label == "matches" and existing_matches and not config.full_refresh:
                        LOGGER.info("No matches fall in the configured refresh window")
                    elif label == "standings" and selected.get("type") in {"CUP", "PLAYOFFS"}:
                        pass
                    else:
                        LOGGER.warning("Empty %s response; check competition, season and API access", label)
            # Ensure the selected competition exists even if the listing was filtered.
            selected_competitions = list(competitions)
            if not any(item.get("id") == selected["id"] for item in selected_competitions):
                selected_competitions.append(selected)
            batches = (
                ("competitions", "competition_id", competition_rows(selected_competitions, run_id)),
                ("teams", "team_id", team_rows(teams, run_id, selected["id"], config.season, config.competition)),
                ("matches", "match_id", match_rows(matches, run_id, config.season, config.competition)),
                ("standings", "standing_key", standings),
            )
            connection.execute("BEGIN TRANSACTION")
            transaction_open = True
            for table, key, rows in batches:
                new, changed = upsert_rows(connection, table, key, rows)
                received += len(rows)
                inserted += new
                updated += changed
                LOGGER.info("%s: new=%s updated=%s", table, new, changed)
            connection.execute("COMMIT")
            transaction_open = False
            finish_run(connection, run_id, "SUCCESS", received, inserted, updated)
            LOGGER.info("Ingestion completed successfully: run_id=%s", run_id)
        except Exception as exc:
            if transaction_open:
                connection.execute("ROLLBACK")
            finish_run(connection, run_id, "FAILED", received, 0, 0, str(exc))
            LOGGER.exception("Ingestion failed: run_id=%s", run_id)
            raise
    return run_id


def _record_skip(config: Config, run_id: str, competition: str, reason: str) -> None:
    """Persist an honest SKIPPED run row without touching raw tables."""
    with connect(config.duckdb_path) as connection:
        create_tables(connection)
        start_run(connection, run_id)
        mark_skipped(connection, run_id, f"{competition}: {reason}")


def ingest_all(config: Config, client: FootballDataClient | None = None,
               today: date | None = None) -> dict[str, dict[str, str]]:
    """Refresh every configured competition; per-competition run rows.

    Returns {code: {"status": ..., "run_id": ...}}. A competition that is
    absent, plan-locked, or season-less records SKIPPED and never aborts the
    others. Genuine errors record FAILED inside ingest(); the summary lets
    main() exit non-zero without hiding which competition failed.
    """
    client = client or FootballDataClient(config.api_token, config.api_base_url,
                                          config.api_timeout, config.api_max_retries,
                                          config.api_pace_seconds)
    summary: dict[str, dict[str, str]] = {}
    with connect(config.duckdb_path) as connection:
        create_tables(connection)
        try:
            competitions = client.get_competitions().get("competitions", [])
        except Exception as exc:
            run_id = str(uuid4())
            start_run(connection, run_id)
            finish_run(connection, run_id, "FAILED", 0, 0, 0,
                       f"competition listing failed: {exc}")
            raise
    if not isinstance(competitions, list):
        raise ValueError("Invalid competitions list in API response")
    for index, code in enumerate(config.competitions):
        if index and config.api_pace_seconds > 0:
            time.sleep(config.api_pace_seconds)
        run_id = str(uuid4())
        try:
            season = config.season
            if season is None:
                season = discover_season(competitions, code)
            single = dataclasses.replace(config, competition=code, season=season)
            ingest(single, client=client, today=today, run_id=run_id)
            summary[code] = {"status": "SUCCESS", "run_id": run_id}
        except ValueError as exc:
            _record_skip(config, run_id, code, str(exc))
            LOGGER.error("Skipped %s: %s", code, exc)
            summary[code] = {"status": "SKIPPED", "run_id": run_id}
        except RuntimeError as exc:
            if any(marker in str(exc) for marker in SKIP_HTTP):
                with connect(config.duckdb_path) as connection:
                    mark_skipped(connection, run_id,
                                 f"{code}: unavailable ({exc})")
                LOGGER.error("Skipped %s: %s", code, exc)
                summary[code] = {"status": "SKIPPED", "run_id": run_id}
            else:
                LOGGER.exception("Failed %s: run_id=%s", code, run_id)
                summary[code] = {"status": "FAILED", "run_id": run_id}
    return summary


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        summary = ingest_all(Config.from_env())
    except Exception as exc:
        LOGGER.error("Pipeline stopped: %s", exc)
        return 1
    failed = sorted(code for code, row in summary.items() if row["status"] == "FAILED")
    skipped = sorted(code for code, row in summary.items() if row["status"] == "SKIPPED")
    LOGGER.info("Summary: %s",
                ", ".join(f"{code}={row['status']}" for code, row in summary.items()))
    if skipped:
        LOGGER.info("Skipped competitions (data preserved): %s", ", ".join(skipped))
    if failed:
        LOGGER.error("Failed competitions: %s", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

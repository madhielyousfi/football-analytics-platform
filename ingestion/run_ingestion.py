"""Run full or rolling-window ingestion into DuckDB raw tables."""

from datetime import date, datetime, timedelta, timezone
import logging
import sys
from uuid import uuid4

from ingestion.api_client import FootballDataClient
from ingestion.config import Config
from ingestion.database import connect, create_tables, finish_run, start_run, upsert_rows
from ingestion.ingest_competitions import competition_rows
from ingestion.ingest_matches import match_rows
from ingestion.ingest_standings import standing_rows
from ingestion.ingest_teams import team_rows

LOGGER = logging.getLogger(__name__)


def ingest(config: Config, client: FootballDataClient | None = None,
           today: date | None = None) -> str:
    """Fetch source data and commit all raw tables as one batch."""
    client = client or FootballDataClient(config.api_token, config.api_base_url,
                                          config.api_timeout, config.api_max_retries)
    run_id = str(uuid4())
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
                LOGGER.info("Standings are unavailable for %s competitions", selected.get("type"))
                standings_response = {"competition": selected, "standings": []}
            else:
                standings_response = client.get_standings(config.competition, config.season)
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


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        ingest(Config.from_env())
        return 0
    except Exception as exc:
        LOGGER.error("Pipeline stopped: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

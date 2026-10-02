"""DuckDB schema, run tracking and idempotent raw writes."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterator

import duckdb


@contextmanager
def connect(path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Create a local database and close its connection reliably."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(path))
    try:
        yield connection
    finally:
        connection.close()


def create_tables(connection: duckdb.DuckDBPyConnection) -> None:
    """Initialize raw and metadata objects without clearing prior data."""
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw_af")
    connection.execute("CREATE SCHEMA IF NOT EXISTS metadata")
    connection.execute("""CREATE TABLE IF NOT EXISTS metadata.pipeline_runs (
        run_id VARCHAR PRIMARY KEY, pipeline_name VARCHAR NOT NULL,
        started_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ,
        status VARCHAR NOT NULL, rows_received INTEGER DEFAULT 0,
        rows_inserted INTEGER DEFAULT 0, rows_updated INTEGER DEFAULT 0,
        error_message VARCHAR
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS raw.competitions (
        competition_id INTEGER PRIMARY KEY, name VARCHAR, code VARCHAR,
        type VARCHAR, area_name VARCHAR, current_season_id INTEGER,
        _payload JSON, _ingested_at TIMESTAMPTZ, _batch_id VARCHAR,
        _source VARCHAR, _api_endpoint VARCHAR
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS raw.teams (
        team_id INTEGER PRIMARY KEY, name VARCHAR, short_name VARCHAR,
        tla VARCHAR, country VARCHAR, founded INTEGER, venue VARCHAR,
        club_colors VARCHAR, crest_url VARCHAR, competition_id INTEGER,
        _season INTEGER, _payload JSON, _ingested_at TIMESTAMPTZ,
        _batch_id VARCHAR, _source VARCHAR, _api_endpoint VARCHAR
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS raw.matches (
        match_id INTEGER PRIMARY KEY, competition_id INTEGER,
        competition_name VARCHAR, season_id INTEGER,
        season_start_date DATE, season_end_date DATE, utc_date TIMESTAMPTZ,
        status VARCHAR, matchday INTEGER, stage VARCHAR,
        home_team_id INTEGER, home_team_name VARCHAR,
        away_team_id INTEGER, away_team_name VARCHAR,
        home_score INTEGER, away_score INTEGER, winner VARCHAR,
        duration VARCHAR, _season INTEGER, _competition VARCHAR,
        _payload JSON, _ingested_at TIMESTAMPTZ, _batch_id VARCHAR,
        _source VARCHAR, _api_endpoint VARCHAR
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS raw.standings (
        standing_key VARCHAR PRIMARY KEY, competition_id INTEGER,
        season_id INTEGER, team_id INTEGER, team_name VARCHAR,
        standing_type VARCHAR, stage VARCHAR, group_name VARCHAR,
        position INTEGER, played_games INTEGER, won INTEGER, draw INTEGER,
        lost INTEGER, points INTEGER, goals_for INTEGER,
        goals_against INTEGER, goal_difference INTEGER, form VARCHAR,
        _season INTEGER, _competition VARCHAR, _payload JSON,
        _ingested_at TIMESTAMPTZ, _batch_id VARCHAR,
        _source VARCHAR, _api_endpoint VARCHAR
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS raw_af.fixtures (
        fixture_id INTEGER PRIMARY KEY, league_id INTEGER,
        league_name VARCHAR, season INTEGER, round VARCHAR,
        fixture_date TIMESTAMPTZ, timestamp BIGINT,
        status_long VARCHAR, status_short VARCHAR, elapsed INTEGER,
        home_team_id INTEGER, home_team_name VARCHAR, home_winner BOOLEAN,
        away_team_id INTEGER, away_team_name VARCHAR, away_winner BOOLEAN,
        goals_home INTEGER, goals_away INTEGER,
        _payload JSON, _ingested_at TIMESTAMPTZ, _batch_id VARCHAR,
        _source VARCHAR, _api_endpoint VARCHAR
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS raw_af.events (
        event_key VARCHAR PRIMARY KEY, fixture_id INTEGER,
        elapsed INTEGER, extra_minute INTEGER,
        team_id INTEGER, team_name VARCHAR,
        player_id INTEGER, player_name VARCHAR,
        assist_player_id INTEGER, assist_player_name VARCHAR,
        event_type VARCHAR, detail VARCHAR, comments VARCHAR,
        _payload JSON, _ingested_at TIMESTAMPTZ, _batch_id VARCHAR,
        _source VARCHAR, _api_endpoint VARCHAR
    )""")


def start_run(connection: duckdb.DuckDBPyConnection, run_id: str,
              pipeline: str = "football_ingestion") -> None:
    connection.execute("""INSERT INTO metadata.pipeline_runs
        (run_id, pipeline_name, started_at, status)
        VALUES (?, ?, ?, 'RUNNING')""",
        [run_id, pipeline, datetime.now(timezone.utc)])


def finish_run(connection: duckdb.DuckDBPyConnection, run_id: str, status: str,
               received: int = 0, inserted: int = 0, updated: int = 0,
               error: str | None = None) -> None:
    connection.execute("""UPDATE metadata.pipeline_runs
        SET completed_at = ?, status = ?, rows_received = ?,
            rows_inserted = ?, rows_updated = ?, error_message = ?
        WHERE run_id = ?""", [datetime.now(timezone.utc), status,
                               received, inserted, updated, error, run_id])


def upsert_rows(connection: duckdb.DuckDBPyConnection, table: str, key: str,
                 rows: list[dict[str, Any]], schema: str = "raw") -> tuple[int, int]:
    """Replace keyed source records atomically within the caller's transaction."""
    allowed = {"competitions", "teams", "matches", "standings"} if schema == "raw" \
        else {"fixtures", "events"} if schema == "raw_af" else set()
    if table not in allowed:
        raise ValueError("Unsupported raw table")
    if not rows:
        return 0, 0
    columns = list(rows[0])
    if key not in columns or any(row.get(key) is None for row in rows):
        raise ValueError(f"Missing {key} in {table} input")
    if any(set(row) != set(columns) for row in rows):
        raise ValueError("Rows have inconsistent columns")
    # Collapse repeated IDs in a single API response; newest occurrence wins.
    unique = {row[key]: row for row in rows}
    keys = list(unique)
    existing = {record[0] for record in connection.execute(
        f"SELECT {key} FROM {schema}.{table} WHERE {key} IN ({', '.join('?' for _ in keys)})", keys
    ).fetchall()}
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    update_sql = ", ".join(f"{col} = EXCLUDED.{col}" for col in columns if col != key)
    statement = (f"INSERT INTO {schema}.{table} ({column_sql}) VALUES ({placeholders}) "
                 f"ON CONFLICT ({key}) DO UPDATE SET {update_sql}")
    for row in unique.values():
        connection.execute(statement, [json.dumps(value) if isinstance(value, (dict, list))
                                       else value for value in (row[col] for col in columns)])
    return len(keys) - len(existing), len(existing)

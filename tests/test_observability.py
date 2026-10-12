"""Validation helpers, error classification, and run-table migration (offline)."""

import duckdb
import pytest

from ingestion import database as db
from ingestion.validate import classify_error, split_valid


def test_split_valid_partitions_and_counts() -> None:
    valid, rejected = split_valid(
        [{"id": 1}, {"id": None}, {"noid": 2}, "junk", {"id": 3}], "id", "teams")
    assert valid == [{"id": 1}, {"id": 3}]
    assert rejected == 3


def test_split_valid_rejects_non_list_envelope() -> None:
    with pytest.raises(ValueError, match="Invalid matches list"):
        split_valid({"matches": []}, "id", "matches")


def test_classify_error_categories() -> None:
    assert classify_error(RuntimeError("API HTTP 401 for /x")) == "AUTH"
    assert classify_error(RuntimeError("API HTTP 429 for /x")) == "RATE_LIMIT"
    assert classify_error(RuntimeError("quota exhausted")) == "RATE_LIMIT"
    assert classify_error(RuntimeError("API HTTP 403 for /x")) == "PLAN"
    assert classify_error(RuntimeError("API request failed for /x")) == "NETWORK"
    assert classify_error(TimeoutError("slow")) == "NETWORK"
    assert classify_error(ValueError("Invalid teams list in API response")) == "VALIDATION"
    assert classify_error(RuntimeError("boom")) == "UNKNOWN"


def test_migration_adds_observability_columns_idempotently() -> None:
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA metadata")
    con.execute("""CREATE TABLE metadata.pipeline_runs (
        run_id VARCHAR PRIMARY KEY, pipeline_name VARCHAR NOT NULL,
        started_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ,
        status VARCHAR NOT NULL, rows_received INTEGER DEFAULT 0,
        rows_inserted INTEGER DEFAULT 0, rows_updated INTEGER DEFAULT 0,
        error_message VARCHAR)""")
    db.ensure_pipeline_run_columns(con)
    db.ensure_pipeline_run_columns(con)
    cols = {row[0] for row in con.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_schema = 'metadata' AND table_name = 'pipeline_runs'""").fetchall()}
    assert {"competition", "season", "api_requests", "rows_rejected",
            "error_category"} <= cols


def test_start_finish_roundtrip_new_fields(tmp_path=None) -> None:
    con = duckdb.connect(":memory:")
    db.create_tables(con)
    db.start_run(con, "r1", competition="PD", season=2026)
    db.finish_run(con, "r1", "SUCCESS", 10, 4, 3,
                  api_requests=4, rejected=1, error_category=None)
    row = con.execute(
        "SELECT competition, season, api_requests, rows_rejected, error_category,"
        " date_diff('second', started_at, completed_at) >= 0 AS has_duration"
        " FROM metadata.pipeline_runs WHERE run_id = 'r1'").fetchone()
    assert row[:5] == ("PD", 2026, 4, 1, None)
    assert row[5] is True

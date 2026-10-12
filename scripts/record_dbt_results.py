"""Record dbt run_results.json into DuckDB for the monitoring dashboard.

Reads the machine-readable test/model outcomes dbt writes to target/ and
stores them in metadata.dbt_test_results, plus a dbt_build row in
metadata.pipeline_runs (last successful transformation tracking).

Usage:
    python scripts/record_dbt_results.py --db data/football.duckdb \\
        --run-results football_dbt/target/run_results.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ingestion.database import connect, create_tables, finish_run, start_run


def ensure_results_table(connection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS metadata")
    connection.execute("""CREATE TABLE IF NOT EXISTS metadata.dbt_test_results (
        run_id VARCHAR NOT NULL, recorded_at TIMESTAMPTZ NOT NULL,
        node_name VARCHAR NOT NULL, node_type VARCHAR NOT NULL,
        status VARCHAR NOT NULL, message VARCHAR, execution_time DOUBLE
    )""")


def summarize(results_path: Path, db_path: Path) -> dict:
    """Parse run_results.json, persist outcomes, return counts (no network)."""
    payload = json.loads(results_path.read_text())
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ValueError("Invalid run_results.json: 'results' is not a list")
    run_id = str(uuid4())
    now = datetime.now(timezone.utc)
    passed = failed = 0
    with connect(db_path) as connection:
        create_tables(connection)
        ensure_results_table(connection)
        start_run(connection, run_id, pipeline="dbt_build")
        rows = []
        for result in results:
            unique_id = str(result.get("unique_id", "unknown"))
            node_type = unique_id.split(".")[0] if "." in unique_id else "unknown"
            status = str(result.get("status", "unknown")).lower()
            rows.append((run_id, now, unique_id, node_type, status,
                         str(result.get("message"))[:2000] if result.get("message") else None,
                         result.get("execution_time")))
            if status in ("pass", "success"):
                passed += 1
            elif status in ("fail", "error"):
                failed += 1
        connection.executemany(
            """INSERT INTO metadata.dbt_test_results
               (run_id, recorded_at, node_name, node_type, status, message, execution_time)
               VALUES (?, ?, ?, ?, ?, ?, ?)""", rows)
        overall = "SUCCESS" if failed == 0 else "FAILED"
        finish_run(connection, run_id, overall, len(rows), passed, failed,
                   None if failed == 0 else f"{failed} dbt nodes failed")
    return {"run_id": run_id, "total": len(rows), "passed": passed, "failed": failed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--run-results", type=Path, required=True)
    args = parser.parse_args()
    if not args.run_results.is_file():
        print(f"run_results.json not found: {args.run_results}")
        return 1
    summary = summarize(args.run_results, args.db)
    print(f"DQ results: {summary['passed']}/{summary['total']} passed "
          f"({summary['failed']} failed), run {summary['run_id']}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

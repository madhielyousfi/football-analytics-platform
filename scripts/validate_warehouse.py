"""Pre-publication warehouse gate: integrity, counts, and DQ status.

Fails (exit 1) when the database must NOT be published as the latest valid
warehouse. Run after dbt build, before artifact upload: a failure skips the
upload step, retaining the previous artifact version.

Usage:
    python scripts/validate_warehouse.py --db data/football.duckdb [--min-matches 1]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def validate(db_path: Path, min_matches: int = 1) -> list[str]:
    """Return a list of blocking problems (empty = publishable)."""
    problems: list[str] = []
    if not db_path.is_file():
        return [f"database file missing: {db_path}"]
    try:
        connection = duckdb.connect(str(db_path), read_only=True)
    except Exception as exc:
        return [f"database file unreadable (corrupt?): {exc}"]
    with connection:
        for schema, table in (("marts", "fact_matches"), ("raw", "matches"),
                              ("metadata", "pipeline_runs")):
            try:
                # storage_info forces page reads (corruption probe); the count
                # forces a full scan of each required table.
                connection.execute(f"PRAGMA storage_info('{schema}.{table}')").fetchall()
                connection.execute(f"SELECT COUNT(*) FROM {schema}.{table}").fetchone()
            except Exception as exc:
                problems.append(f"{schema}.{table} unreadable: {exc}")
        if not problems:
            matches = connection.execute("SELECT COUNT(*) FROM marts.fact_matches").fetchone()[0]
            if matches < min_matches:
                problems.append(f"fact_matches has {matches} rows (< {min_matches})")
            try:
                dq_failed = connection.execute(
                    """SELECT COUNT(*) FROM metadata.dbt_test_results
                       WHERE status IN ('fail', 'error')
                       AND recorded_at >= now() - INTERVAL 1 DAY""").fetchone()[0]
                if dq_failed:
                    problems.append(f"{dq_failed} failed dbt tests in the last 24h")
            except Exception:
                pass  # results table absent on old databases: not blocking
            failed_runs = connection.execute(
                """SELECT COUNT(*) FROM metadata.pipeline_runs
                   WHERE status = 'FAILED' AND started_at >= now() - INTERVAL 1 DAY""").fetchone()[0]
            if failed_runs:
                print(f"Note: {failed_runs} FAILED runs in the last 24h "
                      "(rolled back; not blocking publication).")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--min-matches", type=int, default=1)
    args = parser.parse_args()
    problems = validate(args.db, args.min_matches)
    if problems:
        print("Warehouse gate FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"Warehouse gate passed: {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

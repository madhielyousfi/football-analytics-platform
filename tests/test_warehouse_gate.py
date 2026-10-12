"""Warehouse validation gate (offline, temp databases)."""

from pathlib import Path

import duckdb

from ingestion import database as db
from scripts.validate_warehouse import validate


def make_db(path: Path, matches: int = 2) -> Path:
    db_path = path / "gate.duckdb"
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS marts")
        con.execute("CREATE TABLE marts.fact_matches (match_id INTEGER)")
        if matches:
            con.executemany("INSERT INTO marts.fact_matches VALUES (?)",
                            [(i,) for i in range(matches)])
    with db.connect(db_path) as con:
        db.create_tables(con)
    return db_path


def test_healthy_warehouse_passes(tmp_path: Path) -> None:
    assert validate(make_db(tmp_path)) == []


def test_missing_file_blocks() -> None:
    problems = validate(Path("/nonexistent/x.duckdb"))
    assert any("missing" in p for p in problems)


def test_empty_marts_block(tmp_path: Path) -> None:
    assert any("0 rows" in p for p in validate(make_db(tmp_path, matches=0)))


def test_corrupted_file_blocks(tmp_path: Path) -> None:
    bad = tmp_path / "bad.duckdb"
    bad.write_bytes(b"not a duckdb file at all")
    problems = validate(bad)
    assert problems, "corrupted file must not validate"


def test_failed_runs_warn_but_do_not_block(tmp_path: Path) -> None:
    db_path = make_db(tmp_path)
    with db.connect(db_path) as con:
        db.start_run(con, "r1")
        db.finish_run(con, "r1", "FAILED", error="boom")
    assert validate(db_path) == []

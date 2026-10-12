"""dbt results recorder (fabricated run_results.json, temp database)."""

import json
from pathlib import Path

import duckdb

from scripts.record_dbt_results import summarize


def write_results(tmp_path: Path, nodes: list[dict]) -> Path:
    path = tmp_path / "run_results.json"
    path.write_text(json.dumps({"results": nodes, "elapsed_time": 1.0}))
    return path


def node(uid: str, status: str) -> dict:
    return {"unique_id": uid, "status": status, "message": None, "execution_time": 0.1}


def test_all_pass_records_success(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    summary = summarize(write_results(tmp_path, [
        node("test.a", "pass"), node("model.b", "success")]), db)
    assert summary == {"run_id": summary["run_id"], "total": 2, "passed": 2, "failed": 0}
    with duckdb.connect(str(db), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM metadata.dbt_test_results").fetchone()[0] == 2
        row = con.execute("SELECT status FROM metadata.pipeline_runs").fetchone()
        assert row[0] == "SUCCESS"


def test_failure_records_failed_build(tmp_path: Path) -> None:
    db = tmp_path / "t.duckdb"
    summary = summarize(write_results(tmp_path, [
        node("test.a", "pass"), node("test.b", "fail")]), db)
    assert summary["failed"] == 1
    with duckdb.connect(str(db), read_only=True) as con:
        assert con.execute("SELECT status FROM metadata.pipeline_runs").fetchone()[0] == "FAILED"


def test_malformed_results_rejected(tmp_path: Path) -> None:
    import pytest
    db = tmp_path / "t.duckdb"
    path = tmp_path / "run_results.json"
    path.write_text(json.dumps({"results": {"not": "a list"}}))
    with pytest.raises(ValueError, match="not a list"):
        summarize(path, db)

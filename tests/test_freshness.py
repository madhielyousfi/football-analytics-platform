"""Freshness computation over fabricated run rows (no database)."""

from datetime import datetime, timedelta, timezone

from api.freshness import (
    active_incidents,
    per_competition_freshness,
    status_for_age,
)

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)


def run(status: str, hours_ago: float, comp: str = "PL", inserted: int = 5) -> dict:
    moment = (NOW - timedelta(hours=hours_ago)).isoformat()
    return {"run_id": f"{status}-{hours_ago}", "pipeline_name": "football_ingestion",
            "competition": comp, "season": 2026, "started_at": moment,
            "completed_at": moment, "status": status,
            "rows_inserted": inserted, "rows_updated": 0,
            "error_message": None, "error_category": None}


def scope(comp: str = "PL") -> list[dict]:
    return [{"competition_id": 2021, "competition": comp, "season": 2026}]


def test_age_thresholds() -> None:
    assert status_for_age(None) == "UNKNOWN"
    assert status_for_age(2) == "HEALTHY"
    assert status_for_age(8) == "WARNING"
    assert status_for_age(14) == "CRITICAL"


def test_healthy_reports_change_flag() -> None:
    (healthy,) = per_competition_freshness([run("SUCCESS", 2)], scope(), NOW)
    assert healthy["status"] == "HEALTHY" and healthy["matches_changed"] is True
    assert healthy["hours_since_success"] == 2


def test_success_without_changes_is_healthy_with_note() -> None:
    (row,) = per_competition_freshness([run("SUCCESS", 1, inserted=0)], scope(), NOW)
    assert row["status"] == "HEALTHY" and row["matches_changed"] is False
    assert "no changed matches" in (row["note"] or "")


def test_warning_and_critical_bands() -> None:
    (w,) = per_competition_freshness([run("SUCCESS", 10)], scope(), NOW)
    (c,) = per_competition_freshness([run("SUCCESS", 20)], scope(), NOW)
    assert w["status"] == "WARNING" and c["status"] == "CRITICAL"


def test_never_succeeded_is_unknown_with_failure_count() -> None:
    rows = [run("FAILED", 1), run("FAILED", 7), run("SKIPPED", 30)]
    (row,) = per_competition_freshness(rows, scope(), NOW)
    assert row["status"] == "UNKNOWN" and row["consecutive_failures"] == 2


def test_active_incidents_carry_remediation() -> None:
    bad = run("FAILED", 1)
    bad["error_category"] = "AUTH"
    incidents = active_incidents([bad, run("SUCCESS", 30)])
    assert len(incidents) == 1
    assert "FOOTBALL_API_TOKEN" in incidents[0]["remediation"]
    assert "recovery" in incidents[0]


def test_resolved_pipeline_has_no_incident() -> None:
    assert active_incidents([run("FAILED", 30), run("SUCCESS", 1)]) == []

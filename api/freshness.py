"""Freshness and incident computation over persisted run rows (no I/O)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

WARN_HOURS = 8.0
CRIT_HOURS = 14.0

REMEDIATION = {
    "AUTH": "Verify the FOOTBALL_API_TOKEN secret is set and unexpired.",
    "RATE_LIMIT": "Back off; the next scheduled window recovers automatically.",
    "PLAN": "Point the job at a covered competition/season or upgrade the API plan.",
    "NETWORK": "Transient connectivity issue; the next window retries automatically.",
    "VALIDATION": "Inspect the error message: the API response shape may have changed.",
    "UNKNOWN": "Inspect the run logs for the full traceback.",
}


def _hours_between(now: datetime, then: datetime | str | None) -> float | None:
    if then is None:
        return None
    moment = then if isinstance(then, datetime) else datetime.fromisoformat(str(then))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return max(0.0, (now - moment).total_seconds() / 3600.0)


def status_for_age(hours: float | None) -> str:
    """HEALTHY/WARNING/CRITICAL/UNKNOWN from hours since last success."""
    if hours is None:
        return "UNKNOWN"
    if hours >= CRIT_HOURS:
        return "CRITICAL"
    if hours >= WARN_HOURS:
        return "WARNING"
    return "HEALTHY"


def per_competition_freshness(runs: list[dict[str, Any]],
                             current: list[dict[str, Any]],
                             now: datetime | None = None) -> list[dict[str, Any]]:
    """Freshness per current competition-season from run history.

    `runs`: pipeline_runs rows (newest first ideally; function sorts).
    `current`: [{"competition_id", "competition", "season"}] scoping what
    should stay fresh. Older seasons report UNKNOWN (archived, not stale).
    """
    moment = now or datetime.now(timezone.utc)
    ordered = sorted(runs, key=lambda r: str(r.get("started_at") or ""), reverse=True)
    out = []
    for scope in current:
        comp_runs = [r for r in ordered
                     if r.get("competition") == scope.get("competition")
                     and (r.get("season") == scope.get("season") or r.get("season") is None)]
        successes = [r for r in comp_runs if r.get("status") == "SUCCESS"]
        last = comp_runs[0] if comp_runs else None
        if successes:
            latest = successes[0]
            hours = _hours_between(moment, latest.get("completed_at"))
            changed = (latest.get("rows_inserted") or 0) + (latest.get("rows_updated") or 0) > 0
            out.append({
                "competition": scope.get("competition"), "season": scope.get("season"),
                "status": status_for_age(hours),
                "hours_since_success": round(hours, 2) if hours is not None else None,
                "last_success": latest.get("completed_at"),
                "last_status": last.get("status") if last else None,
                "matches_changed": changed,
                "consecutive_failures": 0,
                "note": None if changed else "Last refresh succeeded with no changed matches.",
            })
        else:
            failures = 0
            for row in comp_runs:
                if row.get("status") == "FAILED":
                    failures += 1
                else:
                    break
            out.append({
                "competition": scope.get("competition"), "season": scope.get("season"),
                "status": "UNKNOWN",
                "hours_since_success": None,
                "last_success": None,
                "last_status": last.get("status") if last else None,
                "matches_changed": False,
                "consecutive_failures": failures,
                "note": "No successful refresh recorded yet.",
            })
    return out


def active_incidents(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Latest run per pipeline+competition that ended FAILED (with remediation)."""
    latest: dict[tuple, dict[str, Any]] = {}
    for row in sorted(runs, key=lambda r: str(r.get("started_at") or "")):
        latest[(row.get("pipeline_name"), row.get("competition"))] = row
    incidents = []
    for (pipeline, competition), row in latest.items():
        if row.get("status") != "FAILED":
            continue
        category = row.get("error_category") or "UNKNOWN"
        incidents.append({
            "pipeline": pipeline, "competition": competition,
            "run_id": row.get("run_id"), "failed_at": row.get("completed_at"),
            "category": category,
            "reason": row.get("error_message"),
            "remediation": REMEDIATION.get(category, REMEDIATION["UNKNOWN"]),
            "recovery": "Next scheduled run retries automatically; prior data preserved by rollback.",
        })
    return incidents

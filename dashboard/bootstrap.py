"""Opt-in warehouse bootstrap for ephemeral Streamlit Cloud instances."""

import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from threading import Lock

from dashboard.database import PROJECT_ROOT, database_path, ensure_analytics_ready

LOGGER = logging.getLogger(__name__)
_BOOTSTRAP_LOCK = Lock()


def _safe_failure_reason(stage: str, detail: str) -> str:
    """Extract an actionable category without exposing response bodies or secrets."""
    if stage != "ingestion":
        return "See the Streamlit Cloud logs for the dbt error."
    http_error = re.search(r"API HTTP (\d{3}) for (/[^\s]+)", detail)
    if http_error:
        status, endpoint = http_error.groups()
        if status in {"401", "403"}:
            return f"Football API HTTP {status} at {endpoint}. Check the Cloud API token and its access."
        if status == "429":
            return "Football API rate limit reached (HTTP 429). Retry after the API limit resets."
        if status in {"400", "404"}:
            return f"Football API HTTP {status} at {endpoint}. Check competition and season settings."
        return f"Football API returned HTTP {status} at {endpoint}."
    if "API request failed for" in detail or "NameResolutionError" in detail:
        return "Could not reach football-data.org from this instance."
    if "Invalid JSON" in detail:
        return "Football API returned invalid JSON."
    return "See the Streamlit Cloud logs for the ingestion error."


def auto_bootstrap_enabled() -> bool:
    """Require explicit opt-in; local dashboard behavior stays unchanged."""
    return os.getenv("FOOTBALL_AUTO_BOOTSTRAP", "false").strip().lower() in {
        "true", "1", "yes",
    }


def _run_step(command: list[str], cwd: Path, env: dict[str, str], stage: str) -> None:
    """Run one bounded setup step and keep the token out of logs."""
    try:
        result = subprocess.run(
            command, cwd=cwd, env=env, check=True,
            capture_output=True, text=True, timeout=600,
        )
        LOGGER.info("Cloud bootstrap %s completed", stage)
        if result.stdout:
            LOGGER.debug("Cloud bootstrap %s output: %s", stage, result.stdout[-1000:])
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or ""
        token = env.get("FOOTBALL_API_TOKEN", "")
        if token:
            detail = detail.replace(token, "[REDACTED]")
        LOGGER.error("Cloud bootstrap %s failed: %s", stage, detail[-1000:])
        reason = _safe_failure_reason(stage, detail)
        raise RuntimeError(f"Automatic {stage} failed. {reason}") from exc


def ensure_or_bootstrap() -> bool:
    """Build an ephemeral warehouse only when enabled and marts are absent.

    Returns True when a build ran. Concurrent sessions in one process share a lock.
    """
    try:
        ensure_analytics_ready()
        return False
    except (FileNotFoundError, RuntimeError):
        if not auto_bootstrap_enabled():
            raise

    with _BOOTSTRAP_LOCK:
        # A second session may have completed the build while waiting.
        try:
            ensure_analytics_ready()
            return False
        except (FileNotFoundError, RuntimeError):
            pass

        if not os.getenv("FOOTBALL_API_TOKEN", "").strip():
            raise RuntimeError(
                "FOOTBALL_API_TOKEN is required in Streamlit Cloud secrets "
                "when FOOTBALL_AUTO_BOOTSTRAP is enabled."
            )
        dbt = Path(sys.executable).with_name("dbt")
        if not dbt.is_file():
            dbt_path = shutil.which("dbt")
            if dbt_path is None:
                raise RuntimeError("dbt is not installed. Install requirements.txt first.")
            dbt = Path(dbt_path)
        env = dict(os.environ, DBT_DUCKDB_PATH=str(database_path()))
        LOGGER.info("Building ephemeral football warehouse for the dashboard")
        _run_step([sys.executable, "-m", "ingestion.run_ingestion"],
                  PROJECT_ROOT, env, "ingestion")
        _run_step([str(dbt), "build", "--profiles-dir", "."],
                  PROJECT_ROOT / "football_dbt", env, "dbt build")
        ensure_analytics_ready()
        return True

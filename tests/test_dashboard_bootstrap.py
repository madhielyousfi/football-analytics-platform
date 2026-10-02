"""Cloud startup only builds a warehouse when explicitly requested."""

from pathlib import Path

import pytest

from dashboard import bootstrap


@pytest.mark.parametrize(
    ("detail", "expected"),
    [
        ("RuntimeError: API HTTP 403 for /competitions", "Check the Cloud API token"),
        ("RuntimeError: API HTTP 429 for /competitions", "rate limit reached"),
        ("RuntimeError: API request failed for /competitions", "Could not reach"),
    ],
)
def test_safe_failure_reason(detail: str, expected: str) -> None:
    assert expected in bootstrap._safe_failure_reason("ingestion", detail)


def test_ready_warehouse_does_not_trigger_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOOTBALL_AUTO_BOOTSTRAP", "true")
    monkeypatch.setattr(bootstrap, "ensure_analytics_ready", lambda: None)
    monkeypatch.setattr(bootstrap, "_run_step", lambda *args: pytest.fail("unexpected build"))
    assert bootstrap.ensure_or_bootstrap() is False


def test_missing_warehouse_requires_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FOOTBALL_AUTO_BOOTSTRAP", raising=False)

    def missing() -> None:
        raise FileNotFoundError("database missing")

    monkeypatch.setattr(bootstrap, "ensure_analytics_ready", missing)
    with pytest.raises(FileNotFoundError, match="database missing"):
        bootstrap.ensure_or_bootstrap()


def test_opt_in_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOOTBALL_AUTO_BOOTSTRAP", "true")
    monkeypatch.delenv("FOOTBALL_API_TOKEN", raising=False)

    def missing() -> None:
        raise FileNotFoundError("database missing")

    monkeypatch.setattr(bootstrap, "ensure_analytics_ready", missing)
    with pytest.raises(RuntimeError, match="FOOTBALL_API_TOKEN"):
        bootstrap.ensure_or_bootstrap()


def test_opt_in_runs_ingestion_then_dbt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOOTBALL_AUTO_BOOTSTRAP", "true")
    monkeypatch.setenv("FOOTBALL_API_TOKEN", "test-token")
    calls: list[tuple[list[str], Path, str]] = []
    ready = False

    def check_ready() -> None:
        if not ready:
            raise FileNotFoundError("database missing")

    def run_step(command: list[str], cwd: Path, env: dict[str, str], stage: str) -> None:
        nonlocal ready
        calls.append((command, cwd, stage))
        assert env["DBT_DUCKDB_PATH"] == str(bootstrap.database_path())
        if stage == "dbt build":
            ready = True

    monkeypatch.setattr(bootstrap, "ensure_analytics_ready", check_ready)
    monkeypatch.setattr(bootstrap, "_run_step", run_step)
    monkeypatch.setattr(bootstrap.sys, "executable", str(Path(__file__).parents[1] / ".venv/bin/python"))
    assert bootstrap.ensure_or_bootstrap() is True
    assert [stage for _, _, stage in calls] == ["ingestion", "dbt build"]
    assert calls[0][0][-1] == "ingestion.run_ingestion"
    assert calls[1][0][1] == "build"

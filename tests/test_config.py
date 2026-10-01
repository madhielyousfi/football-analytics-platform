"""Configuration validation without reading the local .env token."""

import pytest

from ingestion import config as module


def test_token_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "load_dotenv", lambda: None)
    monkeypatch.delenv("FOOTBALL_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="FOOTBALL_API_TOKEN"):
        module.Config.from_env()


def test_refresh_window_must_be_nonnegative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "load_dotenv", lambda: None)
    monkeypatch.setenv("FOOTBALL_API_TOKEN", "test")
    monkeypatch.setenv("FOOTBALL_REFRESH_DAYS_BACK", "-1")
    with pytest.raises(ValueError, match="refresh days"):
        module.Config.from_env()

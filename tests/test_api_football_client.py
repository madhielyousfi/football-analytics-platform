"""API-Football client and quota ledger without a real key."""

from datetime import date
from unittest.mock import Mock

import duckdb
import pytest
import requests

from ingestion.api_football_client import (
    ApiFootballClient,
    QuotaExceeded,
    calls_today,
    check_daily_quota,
    record_call,
)

ENVELOPE = {"errors": [], "response": [{"fixture": {"id": 1}}]}


def make_session(payload: dict | None = None) -> requests.Session:
    session = requests.Session()
    session.get = Mock(return_value=Mock(
        status_code=200, headers={}, json=lambda: payload if payload is not None else ENVELOPE))
    return session


def test_auth_header_and_fixture_params() -> None:
    session = make_session()
    client = ApiFootballClient("placeholder", session=session)
    assert client.get_fixtures(live="39-2-140") == ENVELOPE
    assert session.headers["x-apisports-key"] == "placeholder"
    assert session.get.call_args.kwargs["params"] == {"live": "39-2-140"}


def test_envelope_without_response_rejected() -> None:
    session = make_session({"response-missing": True})
    with pytest.raises(ValueError, match="Unexpected API-Football envelope"):
        ApiFootballClient("placeholder", session=session).get_standings(39, 2026)


def test_api_errors_field_rejected() -> None:
    session = make_session({"errors": {"rateLimit": "too many"}, "response": []})
    with pytest.raises(ValueError, match="API-Football errors"):
        ApiFootballClient("placeholder", session=session).get_live_odds()


def test_http_error_does_not_include_key() -> None:
    session = requests.Session()
    response = Mock(status_code=403, headers={})
    response.raise_for_status.side_effect = requests.HTTPError("forbidden")
    session.get = Mock(return_value=response)
    with pytest.raises(RuntimeError, match="API-Football HTTP 403") as exc:
        ApiFootballClient("secret-value", session=session).get_lineups(7)
    assert "secret-value" not in str(exc.value)


def test_missing_key_rejected() -> None:
    with pytest.raises(ValueError, match="key is required"):
        ApiFootballClient("")


def memory_db() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


def test_quota_counts_and_guards_budget() -> None:
    con = memory_db()
    assert calls_today(con) == 0
    assert record_call(con) == 1
    assert record_call(con) == 2
    assert check_daily_quota(con, needed=5, abort_at=90) == 2
    with pytest.raises(QuotaExceeded, match="budget"):
        check_daily_quota(con, needed=89, abort_at=90)


def test_quota_is_per_day() -> None:
    con = memory_db()
    record_call(con, day=date(2026, 1, 1))
    record_call(con, day=date(2026, 1, 1))
    assert calls_today(con, day=date(2026, 1, 1)) == 2
    assert calls_today(con, day=date(2026, 1, 2)) == 0

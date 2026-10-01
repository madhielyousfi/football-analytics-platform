"""HTTP behavior without a real token."""

from unittest.mock import Mock

import pytest
import requests

from ingestion.api_client import FootballDataClient


def test_match_filters_and_auth_header() -> None:
    session = requests.Session()
    session.get = Mock(return_value=Mock(status_code=200, json=lambda: {"matches": []}))
    client = FootballDataClient("placeholder", session=session)
    assert client.get_matches("PL", 2026, date_from="2026-10-01", status="FINISHED") == {"matches": []}
    assert session.headers["X-Auth-Token"] == "placeholder"
    assert session.get.call_args.kwargs["params"] == {
        "season": 2026, "dateFrom": "2026-10-01", "status": "FINISHED"}


def test_http_error_does_not_include_token() -> None:
    session = requests.Session()
    response = Mock(status_code=401)
    response.raise_for_status.side_effect = requests.HTTPError("unauthorized")
    session.get = Mock(return_value=response)
    with pytest.raises(RuntimeError, match="API HTTP 401") as exc:
        FootballDataClient("secret-value", session=session).get_competitions()
    assert "secret-value" not in str(exc.value)

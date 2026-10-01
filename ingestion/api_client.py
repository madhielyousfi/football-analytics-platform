"""Small football-data.org v4 client with bounded retries."""

import logging
import time
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)


class FootballDataClient:
    """Authenticated client; credentials are never included in log messages."""

    def __init__(self, token: str, base_url: str = "https://api.football-data.org/v4",
                 timeout: int = 30, max_retries: int = 3,
                 session: requests.Session | None = None) -> None:
        if not token:
            raise ValueError("API token is required")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update({"X-Auth-Token": token, "Accept": "application/json"})

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}", params=params, timeout=self.timeout
                )
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After", "")
                        delay = min(float(retry_after), 30) if retry_after.isdigit() else min(2 ** attempt, 30)
                        LOGGER.warning("API status %s on %s; retrying", response.status_code, endpoint)
                        time.sleep(delay)
                        continue
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError(f"Unexpected JSON structure from {endpoint}")
                return data
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(f"API request failed for {endpoint}") from exc
                LOGGER.warning("Connection issue on %s; retrying", endpoint)
                time.sleep(min(2 ** attempt, 30))
            except requests.HTTPError as exc:
                raise RuntimeError(f"API HTTP {response.status_code} for {endpoint}") from exc
            except requests.exceptions.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON from {endpoint}") from exc
        raise RuntimeError(f"API request failed for {endpoint}")

    def get_competitions(self) -> dict[str, Any]:
        return self._get("/competitions")

    def get_teams(self, competition: str, season: int | None = None) -> dict[str, Any]:
        return self._get(f"/competitions/{competition}/teams", {"season": season} if season else None)

    def get_standings(self, competition: str, season: int | None = None,
                      matchday: int | None = None) -> dict[str, Any]:
        params = {"season": season, "matchday": matchday}
        return self._get(f"/competitions/{competition}/standings",
                         {key: value for key, value in params.items() if value is not None})

    def get_matches(self, competition: str, season: int | None = None,
                    date_from: str | None = None, date_to: str | None = None,
                    status: str | None = None, matchday: int | None = None) -> dict[str, Any]:
        params = {"season": season, "dateFrom": date_from, "dateTo": date_to,
                  "status": status, "matchday": matchday}
        return self._get(f"/competitions/{competition}/matches",
                         {key: value for key, value in params.items() if value is not None})

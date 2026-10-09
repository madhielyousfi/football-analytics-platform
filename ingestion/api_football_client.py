"""API-Football (api-sports v3) client with daily quota ledger.

Second data source for live scores, events, lineups, player stats, odds.
Free plan: 100 requests/day across ALL endpoints, so every call must be
counted in metadata.api_quota and guarded by check_daily_quota().

Docs: https://www.api-football.com/documentation-v3
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import duckdb
import requests

LOGGER = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_DAILY_LIMIT = 100
DEFAULT_ABORT_AT = 90


class QuotaExceeded(RuntimeError):
    """Raised when the daily API-Football budget is exhausted."""


def ensure_quota_table(connection: duckdb.DuckDBPyConnection) -> None:
    """Create the quota ledger without touching other objects."""
    connection.execute("CREATE SCHEMA IF NOT EXISTS metadata")
    connection.execute("""CREATE TABLE IF NOT EXISTS metadata.api_quota (
        quota_date DATE PRIMARY KEY, calls INTEGER NOT NULL DEFAULT 0
    )""")


def calls_today(connection: duckdb.DuckDBPyConnection, day: date | None = None) -> int:
    """Return calls already spent today (0 when no row exists)."""
    ensure_quota_table(connection)
    day = day or date.today()
    row = connection.execute(
        "SELECT calls FROM metadata.api_quota WHERE quota_date = ?", [day]
    ).fetchone()
    return int(row[0]) if row else 0


def record_call(connection: duckdb.DuckDBPyConnection, day: date | None = None) -> int:
    """Count one spent request; returns the new total for today."""
    ensure_quota_table(connection)
    day = day or date.today()
    connection.execute(
        """INSERT INTO metadata.api_quota (quota_date, calls) VALUES (?, 1)
           ON CONFLICT (quota_date) DO UPDATE SET calls = metadata.api_quota.calls + 1""",
        [day],
    )
    return calls_today(connection, day)


def check_daily_quota(connection: duckdb.DuckDBPyConnection, needed: int = 1,
                      daily_limit: int = DEFAULT_DAILY_LIMIT,
                      abort_at: int = DEFAULT_ABORT_AT,
                      day: date | None = None) -> int:
    """Raise QuotaExceeded if `needed` calls would breach the abort threshold."""
    ensure_quota_table(connection)
    spent = calls_today(connection, day)
    if spent + needed > abort_at:
        raise QuotaExceeded(
            f"API-Football budget: {spent}/{daily_limit} spent, "
            f"need {needed}, abort threshold {abort_at}"
        )
    return spent


class ApiFootballClient:
    """Authenticated client; the key never appears in logs or errors."""

    def __init__(self, key: str, base_url: str = DEFAULT_BASE_URL,
                 timeout: int = 30, max_retries: int = 3,
                 session: requests.Session | None = None) -> None:
        if not key:
            raise ValueError("API-Football key is required")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update({"x-apisports-key": key, "Accept": "application/json"})

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}", params=clean, timeout=self.timeout
                )
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After", "")
                        if retry_after.isdigit():
                            delay = min(float(retry_after), 60)
                        elif response.status_code == 429:
                            delay = min(10 * (attempt + 1), 60)
                        else:
                            delay = min(2 ** attempt, 30)
                        LOGGER.warning("API-Football status %s on %s; retrying in %ss",
                                       response.status_code, endpoint, delay)
                        time.sleep(delay)
                        continue
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or "response" not in data:
                    raise ValueError(f"Unexpected API-Football envelope from {endpoint}")
                errors = data.get("errors")
                if errors:
                    raise ValueError(f"API-Football errors on {endpoint}: {errors}")
                return data
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(f"API-Football request failed for {endpoint}") from exc
                LOGGER.warning("Connection issue on %s; retrying", endpoint)
                time.sleep(min(2 ** attempt, 30))
            except requests.HTTPError as exc:
                raise RuntimeError(f"API-Football HTTP {response.status_code} for {endpoint}") from exc
            except requests.exceptions.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON from {endpoint}") from exc
        raise RuntimeError(f"API-Football request failed for {endpoint}")

    # --- fixtures family (fixture id is the master key) ---
    def get_fixtures(self, live: str | None = None, league: int | None = None,
                     season: int | None = None, date_: str | None = None,
                     fixture_id: int | None = None) -> dict[str, Any]:
        return self._get("/fixtures", {"live": live, "league": league,
                                       "season": season, "date": date_, "id": fixture_id})

    def get_fixture_events(self, fixture_id: int) -> dict[str, Any]:
        return self._get("/fixtures/events", {"fixture": fixture_id})

    def get_lineups(self, fixture_id: int) -> dict[str, Any]:
        return self._get("/fixtures/lineups", {"fixture": fixture_id})

    def get_fixture_statistics(self, fixture_id: int) -> dict[str, Any]:
        return self._get("/fixtures/statistics", {"fixture": fixture_id})

    def get_fixture_players(self, fixture_id: int) -> dict[str, Any]:
        return self._get("/fixtures/players", {"fixture": fixture_id})

    def get_head_to_head(self, home_id: int, away_id: int) -> dict[str, Any]:
        return self._get("/fixtures/headtohead", {"h2h": f"{home_id}-{away_id}"})

    # --- reference data ---
    def get_leagues(self) -> dict[str, Any]:
        return self._get("/leagues")

    def get_standings(self, league: int, season: int) -> dict[str, Any]:
        return self._get("/standings", {"league": league, "season": season})

    def get_top_scorers(self, league: int, season: int) -> dict[str, Any]:
        return self._get("/players/topscorers", {"league": league, "season": season})

    def get_injuries(self, league: int, season: int,
                     fixture_id: int | None = None) -> dict[str, Any]:
        return self._get("/injuries", {"league": league, "season": season,
                                       "fixture": fixture_id})

    def get_predictions(self, fixture_id: int) -> dict[str, Any]:
        return self._get("/predictions", {"fixture": fixture_id})

    def get_odds(self, fixture_id: int | None = None, league: int | None = None,
                 season: int | None = None, date_: str | None = None) -> dict[str, Any]:
        return self._get("/odds", {"fixture": fixture_id, "league": league,
                                   "season": season, "date": date_})

    def get_live_odds(self, fixture_id: int | None = None,
                      league: int | None = None) -> dict[str, Any]:
        return self._get("/odds/live", {"fixture": fixture_id, "league": league})

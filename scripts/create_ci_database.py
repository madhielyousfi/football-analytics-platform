"""Create a tiny, realistic raw DuckDB database for token-free CI."""

import argparse
from pathlib import Path
from typing import Any

from ingestion.config import Config
from ingestion.run_ingestion import ingest


class FixtureClient:
    """Return API-shaped data without making network requests."""

    def get_competitions(self) -> dict[str, Any]:
        return {"competitions": [{
            "id": 2021,
            "name": "Premier League",
            "code": "PL",
            "type": "LEAGUE",
            "area": {"name": "England"},
            "currentSeason": {
                "id": 9000, "startDate": "2026-08-01", "endDate": "2027-05-31"
            },
        }]}

    def get_teams(self, competition: str, season: int) -> dict[str, Any]:
        return {"teams": [
            {"id": 1, "name": "Alpha FC", "shortName": "Alpha", "tla": "ALP",
             "area": {"name": "England"}, "founded": 1901},
            {"id": 2, "name": "Beta FC", "shortName": "Beta", "tla": "BET",
             "area": {"name": "England"}, "founded": 1902},
        ]}

    def get_matches(self, competition: str, season: int,
                    date_from: str | None = None,
                    date_to: str | None = None) -> dict[str, Any]:
        common = {
            "competition": {"id": 2021, "name": "Premier League"},
            "season": {"id": 9000, "startDate": "2026-08-01", "endDate": "2027-05-31"},
            "stage": "REGULAR_SEASON",
            "duration": "REGULAR",
        }
        return {"matches": [
            {**common, "id": 1001, "utcDate": "2026-08-15T15:00:00Z",
             "status": "FINISHED", "matchday": 1,
             "homeTeam": {"id": 1, "name": "Alpha FC"},
             "awayTeam": {"id": 2, "name": "Beta FC"},
             "score": {"winner": "HOME_TEAM", "duration": "REGULAR",
                       "fullTime": {"home": 2, "away": 1}}},
            {**common, "id": 1002, "utcDate": "2026-08-22T15:00:00Z",
             "status": "TIMED", "matchday": 2,
             "homeTeam": {"id": 2, "name": "Beta FC"},
             "awayTeam": {"id": 1, "name": "Alpha FC"},
             "score": {"winner": None, "duration": "REGULAR",
                       "fullTime": {"home": None, "away": None}}},
        ]}

    def get_standings(self, competition: str, season: int) -> dict[str, Any]:
        return {
            "competition": {"id": 2021},
            "season": {"id": 9000},
            "standings": [{
                "stage": "REGULAR_SEASON", "type": "TOTAL", "group": None,
                "table": [
                    {"position": 1, "team": {"id": 1, "name": "Alpha FC"},
                     "playedGames": 1, "won": 1, "draw": 0, "lost": 0,
                     "points": 3, "goalsFor": 2, "goalsAgainst": 1, "goalDifference": 1},
                    {"position": 2, "team": {"id": 2, "name": "Beta FC"},
                     "playedGames": 1, "won": 0, "draw": 0, "lost": 1,
                     "points": 0, "goalsFor": 1, "goalsAgainst": 2, "goalDifference": -1},
                ],
            }],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, required=True,
                        help="Output database path; use a temporary path for CI")
    arguments = parser.parse_args()
    config = Config(
        api_token="ci-fixture", api_base_url="https://example.invalid/v4",
        competition="PL", season=2026, duckdb_path=arguments.db_path,
    )
    run_id = ingest(config, FixtureClient())
    print(f"Created CI database at {arguments.db_path} (run {run_id})")


if __name__ == "__main__":
    main()

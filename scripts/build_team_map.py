"""Build the FD <-> API-Football team map for one league/season (1 AF call).

Usage:
    API_FOOTBALL_KEY=... python scripts/build_team_map.py --league 39 --season 2024 \\
        --competition PL --db data/football.duckdb
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ingestion.api_football_client import ApiFootballClient
from ingestion.database import connect, create_tables
from ingestion.id_map import build_team_map, upsert_team_map

# Hand-verified overrides (FD id -> AF id) for clubs whose names never match.
PL_OVERRIDES = {67: 34, 73: 47, 349: 57, 397: 51, 1044: 35, 76: 39, 338: 46, 563: 48}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", type=int, required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--competition", default="PL")
    parser.add_argument("--db", type=Path, default=Path("data/football.duckdb"))
    args = parser.parse_args()

    key = os.getenv("API_FOOTBALL_KEY", "").strip()
    if not key:
        raise SystemExit("API_FOOTBALL_KEY is required")
    client = ApiFootballClient(key)
    payload = client.get_teams(args.league, args.season)
    af = [{"team_id": t["team"]["id"], "team_name": t["team"]["name"]}
          for t in payload.get("response", [])]
    with connect(args.db) as connection:
        create_tables(connection)
        comp = connection.execute(
            "SELECT competition_id FROM raw.competitions WHERE code = ?",
            [args.competition]).fetchone()
        if comp is None:
            raise SystemExit(f"Competition {args.competition} not ingested yet")
        fd = [{"team_id": row[0], "team_name": row[1]} for row in connection.execute(
            "SELECT DISTINCT team_id, name FROM raw.teams WHERE competition_id = ?",
            [comp[0]]).fetchall()]
        overrides = PL_OVERRIDES if args.competition == "PL" else {}
        rows = build_team_map(fd, af, overrides=overrides)
        upsert_team_map(connection, rows)
        mapped = sum(1 for r in rows if r["af_team_id"] is not None)
        print(f"Mapped {mapped}/{len(rows)} teams for {args.competition}")
        for row in rows:
            if row["af_team_id"] is None:
                print(f"  unmapped: {row['team_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

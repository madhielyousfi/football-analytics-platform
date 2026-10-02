"""Cross-provider identity mapping (football-data.org <-> API-Football).

The two providers use different team/fixture ids. Team identity is mapped by
normalized names with an override file for ambiguous cases; fixtures are
resolved at query time by (date, home/away ids) so no fixture table is needed.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import duckdb

SUFFIXES = {"fc", "cf", "sc", "ac", "afc", "fv", "bk", "if", "fk", "sk", "ssc", "usc", "as"}


def normalize_name(name: str) -> str:
    """Lowercase, strip accents/punctuation; drop trailing club suffix like FC."""
    text = unicodedata.normalize("NFKD", (name or "")).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    words = [w for w in text.split() if w]
    while len(words) > 1 and words[-1] in SUFFIXES:
        words.pop()
    return " ".join(words)


def build_team_map(fd_teams: list[dict[str, Any]],
                   af_teams: list[dict[str, Any]],
                   overrides: dict[int, int] | None = None) -> list[dict[str, Any]]:
    """Match fd team ids to API-Football team ids by normalized name.

    `fd_teams`: [{"team_id", "team_name"}], `af_teams`: [{"team_id", "team_name"}].
    Returns rows with confidence 'override' | 'exact' | 'unmapped'.
    """
    overrides = overrides or {}
    by_name: dict[str, int] = {}
    for team in af_teams:
        by_name.setdefault(normalize_name(str(team.get("team_name"))), int(team["team_id"]))
    rows = []
    for team in fd_teams:
        fd_id = int(team["team_id"])
        if fd_id in overrides:
            rows.append({"fd_team_id": fd_id, "af_team_id": overrides[fd_id],
                         "team_name": team.get("team_name"), "confidence": "override"})
            continue
        af_id = by_name.get(normalize_name(str(team.get("team_name"))))
        rows.append({"fd_team_id": fd_id, "af_team_id": af_id,
                     "team_name": team.get("team_name"),
                     "confidence": "exact" if af_id is not None else "unmapped"})
    return rows


def ensure_map_table(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS metadata")
    connection.execute("""CREATE TABLE IF NOT EXISTS metadata.team_map (
        fd_team_id INTEGER PRIMARY KEY, af_team_id INTEGER,
        team_name VARCHAR, confidence VARCHAR NOT NULL
    )""")


def upsert_team_map(connection: duckdb.DuckDBPyConnection,
                    rows: list[dict[str, Any]]) -> None:
    """Replace team mappings atomically (mapping is fully recomputed)."""
    ensure_map_table(connection)
    connection.execute("DELETE FROM metadata.team_map")
    connection.executemany(
        "INSERT INTO metadata.team_map (fd_team_id, af_team_id, team_name, confidence)"
        " VALUES (?, ?, ?, ?)",
        [(r["fd_team_id"], r["af_team_id"], r.get("team_name"), r["confidence"]) for r in rows],
    )

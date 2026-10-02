"""Read-only analytics API over DuckDB dbt marts.

Run:  uvicorn api.main:app --reload --port 8000
Env:  DUCKDB_PATH (default data/football.duckdb relative to repo root)
"""

from __future__ import annotations

import os
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Optional

import duckdb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI(
    title="Football Intelligence API",
    version="1.0.0",
    description="Read-only JSON over dbt marts (fact_matches, league table, form, goals, H2H).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def db_path() -> Path:
    configured = Path(os.getenv("DUCKDB_PATH", "data/football.duckdb"))
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


def fetch(sql: str, params: Optional[list] = None):
    path = db_path()
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"DuckDB file not found: {path}. Run ingestion + dbt build.")
    try:
        with closing(duckdb.connect(str(path), read_only=True)) as con:
            rel = con.execute(sql, params or [])
            cols = [d[0] for d in rel.description]
            rows = rel.fetchall()
    except duckdb.CatalogException as exc:
        raise HTTPException(status_code=503, detail=f"dbt marts missing ({exc}). Run dbt build.") from exc
    out = []
    for r in rows:
        rec = {}
        for k, v in zip(cols, r):
            if isinstance(v, (date,)):
                rec[k] = v.isoformat()
            elif hasattr(v, "isoformat"):
                try:
                    rec[k] = v.isoformat()
                except Exception:
                    rec[k] = str(v)
            else:
                rec[k] = v
        out.append(rec)
    return out


@app.get("/api/health")
def health():
    path = db_path()
    ok = path.is_file()
    return {"status": "ok" if ok else "missing-db", "db_path": str(path)}


@app.get("/api/competitions")
def competitions():
    rows = fetch(
        """SELECT DISTINCT f.competition_id, c.competition_name, c.competition_code, f.season
           FROM marts.fact_matches f JOIN marts.dim_competition c USING (competition_id)
           ORDER BY c.competition_name, f.season DESC"""
    )
    grouped: dict = {}
    for r in rows:
        cid = r["competition_id"]
        grouped.setdefault(cid, {"competition_id": cid, "competition_name": r["competition_name"],
                                 "competition_code": r.get("competition_code"), "seasons": []})
        grouped[cid]["seasons"].append(r["season"])
    return list(grouped.values())


@app.get("/api/teams")
def teams(competition_id: int, season: int):
    return fetch(
        """SELECT l.team_id, l.team_name, t.crest_url, t.short_name
           FROM marts.mart_league_table l LEFT JOIN marts.dim_team t ON l.team_id=t.team_id
           WHERE l.competition_id=? AND l.season=? ORDER BY l.team_name""",
        [competition_id, season])


@app.get("/api/overview")
def overview(competition_id: int, season: int):
    rows = fetch(
        """SELECT coalesce(g.matches_played,0) AS total_matches, coalesce(g.total_goals,0) AS total_goals,
           coalesce(g.average_goals_per_match,0) AS average_goals_per_match,
           (SELECT count(*) FROM marts.mart_league_table WHERE competition_id=? AND season=?) AS number_of_teams,
           g.matches_over_2_5, g.matches_under_2_5, g.scoreless_draws,
           g.average_home_goals, g.average_away_goals
           FROM (SELECT 1) base LEFT JOIN marts.mart_goal_analysis g
           ON g.competition_id=? AND g.season=?""",
        [competition_id, season, competition_id, season])
    return rows[0] if rows else {}


@app.get("/api/match-outcomes")
def match_outcomes(competition_id: int, season: int):
    rows = fetch(
        """SELECT count(*) AS total_matches,
           count(*) FILTER (WHERE is_home_win) AS home_wins,
           count(*) FILTER (WHERE is_away_win) AS away_wins,
           count(*) FILTER (WHERE is_draw) AS draws
           FROM marts.fact_matches WHERE competition_id=? AND season=? AND is_completed""",
        [competition_id, season])
    return rows[0] if rows else {}


@app.get("/api/league-table")
def league_table(competition_id: int, season: int):
    return fetch(
        """SELECT l.position, l.team_id, l.team_name, t.crest_url, t.short_name,
           l.played, l.wins, l.draws, l.losses, l.goals_for, l.goals_against, l.goal_difference, l.points
           FROM marts.mart_league_table l LEFT JOIN marts.dim_team t ON l.team_id=t.team_id
           WHERE l.competition_id=? AND l.season=? ORDER BY l.position""",
        [competition_id, season])


@app.get("/api/league-comparison")
def league_comparison(competition_id: int, season: int):
    return fetch(
        """SELECT l.position, l.team_id, l.team_name, l.points, l.goals_for, l.goals_against, l.goal_difference,
           p.win_percentage, h.home_wins, h.away_wins, h.home_win_rate, h.away_win_rate
           FROM marts.mart_league_table l
           LEFT JOIN marts.mart_team_performance p ON l.competition_id=p.competition_id AND l.season=p.season AND l.team_id=p.team_id
           LEFT JOIN marts.mart_home_away h ON l.competition_id=h.competition_id AND l.season=h.season AND l.team_id=h.team_id
           WHERE l.competition_id=? AND l.season=? ORDER BY l.position""",
        [competition_id, season])


@app.get("/api/team-performance")
def team_performance(competition_id: int, season: int, team_id: Optional[int] = None):
    return fetch(
        """SELECT * FROM marts.mart_team_performance WHERE competition_id=? AND season=?
           AND (? IS NULL OR team_id=?)""",
        [competition_id, season, team_id, team_id])


@app.get("/api/all-team-form")
def all_team_form(competition_id: int, season: int):
    return fetch(
        """SELECT f.team_id, t.team_name, t.crest_url, f.recent_form, f.points_last_5, f.recent_matches
           FROM marts.mart_team_form f JOIN marts.dim_team t USING (team_id)
           WHERE f.competition_id=? AND f.season=? ORDER BY f.points_last_5 DESC, t.team_name""",
        [competition_id, season])


@app.get("/api/team-form")
def team_form(competition_id: int, season: int, team_id: int):
    rows = fetch("SELECT * FROM marts.mart_team_form WHERE competition_id=? AND season=? AND team_id=?",
                 [competition_id, season, team_id])
    return rows[0] if rows else {}


@app.get("/api/home-away")
def home_away(competition_id: int, season: int, team_id: Optional[int] = None):
    return fetch(
        """SELECT h.*, t.team_name FROM marts.mart_home_away h JOIN marts.dim_team t USING (team_id)
           WHERE h.competition_id=? AND h.season=? AND (? IS NULL OR h.team_id=?)""",
        [competition_id, season, team_id, team_id])


@app.get("/api/goal-trends")
def goal_trends(competition_id: int, season: int):
    return fetch(
        """SELECT match_date, matches_played, goals, home_goals, away_goals,
           round(goals::DOUBLE / nullif(matches_played,0),2) AS average_goals
           FROM marts.mart_goal_trends WHERE competition_id=? AND season=? ORDER BY match_date""",
        [competition_id, season])


@app.get("/api/team-progression")
def team_progression(competition_id: int, season: int, team_id: int):
    return fetch(
        """SELECT match_id, match_date, match_datetime, opponent_name, venue_type, result,
           goals_for, goals_against, points, cumulative_goals, cumulative_points
           FROM marts.mart_team_progression
           WHERE competition_id=? AND season=? AND team_id=? ORDER BY match_datetime, match_id""",
        [competition_id, season, team_id])


@app.get("/api/match-filter-options")
def match_filter_options(competition_id: int, season: int):
    dates = fetch("SELECT min(match_date) AS min_date, max(match_date) AS max_date FROM marts.fact_matches WHERE competition_id=? AND season=?",
                  [competition_id, season])
    matchdays = fetch("SELECT DISTINCT matchday FROM marts.fact_matches WHERE competition_id=? AND season=? AND matchday IS NOT NULL ORDER BY matchday",
                      [competition_id, season])
    statuses = fetch("SELECT DISTINCT match_status FROM marts.fact_matches WHERE competition_id=? AND season=? ORDER BY match_status",
                     [competition_id, season])
    return {"dates": dates[0] if dates else {}, "matchdays": [r["matchday"] for r in matchdays],
            "statuses": [r["match_status"] for r in statuses]}


@app.get("/api/matches")
def matches(
    competition_id: int,
    season: int,
    team_id: Optional[int] = None,
    matchday: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(500, le=2000),
):
    return fetch(
        """SELECT f.match_id, f.match_date, home.team_name AS home_team, home.crest_url AS home_crest_url,
           away.team_name AS away_team, away.crest_url AS away_crest_url,
           f.home_goals, f.away_goals, f.match_status, f.matchday
           FROM marts.fact_matches f
           JOIN marts.dim_team home ON f.home_team_id=home.team_id
           JOIN marts.dim_team away ON f.away_team_id=away.team_id
           WHERE f.competition_id=? AND f.season=?
             AND (? IS NULL OR f.home_team_id=? OR f.away_team_id=?)
             AND (? IS NULL OR f.matchday=?)
             AND (? IS NULL OR f.match_date >= ?)
             AND (? IS NULL OR f.match_date <= ?)
             AND (? IS NULL OR f.match_status=?)
           ORDER BY f.match_date DESC, f.match_id DESC LIMIT ?""",
        [competition_id, season, team_id, team_id, team_id, matchday, matchday,
         start_date, start_date, end_date, end_date, status, status, limit])


@app.get("/api/head-to-head")
def head_to_head(competition_id: int, season: int, team_a_id: int, team_b_id: int):
    rows = fetch(
        """SELECT matches_played, draws, recent_results,
           CASE WHEN team_a_id=? THEN team_a_wins ELSE team_b_wins END AS selected_a_wins,
           CASE WHEN team_a_id=? THEN team_b_wins ELSE team_a_wins END AS selected_b_wins,
           CASE WHEN team_a_id=? THEN team_a_goals ELSE team_b_goals END AS selected_a_goals,
           CASE WHEN team_a_id=? THEN team_b_goals ELSE team_a_goals END AS selected_b_goals
           FROM marts.mart_head_to_head WHERE competition_id=? AND season=?
           AND team_a_id=least(?,?) AND team_b_id=greatest(?,?)""",
        [team_a_id, team_a_id, team_a_id, team_a_id, competition_id, season,
         team_a_id, team_b_id, team_a_id, team_b_id])
    if not rows:
        return {"matches_played": 0, "draws": 0, "selected_a_wins": 0, "selected_b_wins": 0,
                "selected_a_goals": 0, "selected_b_goals": 0, "recent_results": None}
    return rows[0]


@app.get("/api/head-to-head-matches")
def head_to_head_matches(competition_id: int, season: int, team_a_id: int, team_b_id: int):
    return fetch(
        """SELECT f.match_date, home.team_name AS home_team, away.team_name AS away_team,
           f.home_goals, f.away_goals FROM marts.fact_matches f
           JOIN marts.dim_team home ON f.home_team_id=home.team_id
           JOIN marts.dim_team away ON f.away_team_id=away.team_id
           WHERE f.competition_id=? AND f.season=? AND f.is_completed
           AND ((f.home_team_id=? AND f.away_team_id=?) OR (f.home_team_id=? AND f.away_team_id=?))
           ORDER BY f.match_date DESC, f.match_id DESC LIMIT 10""",
        [competition_id, season, team_a_id, team_b_id, team_b_id, team_a_id])


LIVE_STATUSES = ("1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE")


@app.get("/api/live")
def live(league_id: Optional[int] = None, limit: int = Query(100, le=500)):
    """Live now + recent + upcoming fixtures from the API-Football backfill."""
    placeholders = ", ".join("?" for _ in LIVE_STATUSES)
    try:
        return fetch(
            f"""SELECT fixture_id, league_id, league_name, season, round, fixture_date,
               status_long, status_short, elapsed,
               home_team_id, home_team_name, away_team_id, away_team_name,
               goals_home, goals_away
               FROM raw_af.fixtures
               WHERE (? IS NULL OR league_id = ?)
                 AND (status_short IN ({placeholders})
                      OR fixture_date >= current_date - INTERVAL 1 DAY)
               ORDER BY CASE WHEN status_short IN ({placeholders}) THEN 0 ELSE 1 END,
                        fixture_date LIMIT ?""",
            [league_id, league_id, *LIVE_STATUSES, *LIVE_STATUSES, limit])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/pipeline-runs")
def pipeline_runs(limit: int = Query(20, le=100)):
    try:
        return fetch(
            """SELECT run_id, pipeline_name, started_at, completed_at, status,
               rows_received, rows_inserted, rows_updated, error_message,
               date_diff('second', started_at, completed_at) AS duration_seconds
               FROM metadata.pipeline_runs ORDER BY started_at DESC LIMIT ?""", [limit])
    except HTTPException:
        return JSONResponse(content=[])

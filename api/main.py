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
from pydantic import BaseModel

from api.push_store import (
    all_subscriptions as _all_subs,
    ensure_push_tables,
    subscribe as _subscribe,
    unsubscribe as _unsubscribe,
)

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
        """SELECT DISTINCT f.competition_id, c.competition_name, c.competition_code,
           c.competition_type, f.season
           FROM marts.fact_matches f JOIN marts.dim_competition c USING (competition_id)
           ORDER BY c.competition_name, f.season DESC"""
    )
    grouped: dict = {}
    for r in rows:
        cid = r["competition_id"]
        grouped.setdefault(cid, {"competition_id": cid, "competition_name": r["competition_name"],
                                 "competition_code": r.get("competition_code"),
                                 "competition_type": r.get("competition_type"), "seasons": []})
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


class PushSubscription(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    label: str | None = None


class PushEndpoint(BaseModel):
    endpoint: str


@app.get("/api/push/vapid-key")
def vapid_key():
    """Public VAPID key for browser subscription (503 when unconfigured)."""
    key = os.getenv("VAPID_PUBLIC_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="Web Push not configured")
    return {"publicKey": key}


@app.post("/api/push/subscribe")
def push_subscribe(sub: PushSubscription):
    path = db_path()
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Warehouse not initialized")
    with closing(duckdb.connect(str(path))) as con:
        ensure_push_tables(con)
        _subscribe(con, sub.endpoint, sub.p256dh, sub.auth, sub.label)
    return {"ok": True}


@app.post("/api/push/unsubscribe")
def push_unsubscribe(sub: PushEndpoint):
    path = db_path()
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Warehouse not initialized")
    with closing(duckdb.connect(str(path))) as con:
        removed = _unsubscribe(con, sub.endpoint)
    return {"ok": True, "removed": removed}


@app.get("/api/live")
def live(league_id: Optional[int] = None, limit: int = Query(100, le=500)):
    """Live now + recent + upcoming fixtures from the API-Football backfill."""
    placeholders = ", ".join("?" for _ in LIVE_STATUSES)
    params: list = [league_id, league_id, *LIVE_STATUSES, *LIVE_STATUSES, limit]
    where = f"""WHERE (? IS NULL OR f.league_id = ?)
                 AND (f.status_short IN ({placeholders})
                      OR f.fixture_date >= current_date - INTERVAL 1 DAY)
               ORDER BY CASE WHEN f.status_short IN ({placeholders}) THEN 0 ELSE 1 END,
                        f.fixture_date LIMIT ?"""
    enriched = f"""SELECT f.fixture_id, f.league_id, f.league_name, f.season, f.round,
               f.fixture_date, f.status_long, f.status_short, f.elapsed,
               f.home_team_id, f.home_team_name, hd.crest_url AS home_crest_url,
               f.away_team_id, f.away_team_name, ad.crest_url AS away_crest_url,
               f.goals_home, f.goals_away
               FROM raw_af.fixtures f
               LEFT JOIN metadata.team_map hm ON f.home_team_id = hm.af_team_id
               LEFT JOIN marts.dim_team hd ON hm.fd_team_id = hd.team_id
               LEFT JOIN metadata.team_map am ON f.away_team_id = am.af_team_id
               LEFT JOIN marts.dim_team ad ON am.fd_team_id = ad.team_id
               {where}"""
    plain = f"""SELECT f.fixture_id, f.league_id, f.league_name, f.season, f.round,
               f.fixture_date, f.status_long, f.status_short, f.elapsed,
               f.home_team_id, f.home_team_name, NULL AS home_crest_url,
               f.away_team_id, f.away_team_name, NULL AS away_crest_url,
               f.goals_home, f.goals_away
               FROM raw_af.fixtures f
               {where}"""
    try:
        return fetch(enriched, params)
    except HTTPException:
        pass
    try:
        return fetch(plain, params)
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/fixture-detail")
def fixture_detail(fixture_id: int):
    """Header + event timeline for one API-Football fixture."""
    try:
        header = fetch(
            """SELECT fixture_id, league_id, league_name, season, round, fixture_date,
               status_long, status_short, elapsed,
               home_team_id, home_team_name, away_team_id, away_team_name,
               goals_home, goals_away
               FROM raw_af.fixtures WHERE fixture_id = ?""", [fixture_id])
        if not header:
            raise HTTPException(status_code=404, detail="Fixture not backfilled yet")
        events = fetch(
            """SELECT elapsed, extra_minute, team_id, team_name, player_id, player_name,
               assist_player_id, assist_player_name, event_type, detail, comments
               FROM raw_af.events WHERE fixture_id = ?
               ORDER BY elapsed, extra_minute""", [fixture_id])
        return {"fixture": header[0], "events": events}
    except HTTPException:
        raise
    except Exception:
        return JSONResponse(content={"fixture": None, "events": []})


@app.get("/api/fixture-lineups")
def fixture_lineups(fixture_id: int):
    """Starting XIs + benches with formations from the depth backfill."""
    try:
        return fetch(
            """SELECT team_id, team_name, formation, coach_name, player_id,
               player_name, number, position, grid, is_starting
               FROM raw_af.lineups WHERE fixture_id = ?
               ORDER BY team_id, is_starting DESC, number""", [fixture_id])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/fixture-stats")
def fixture_stats(fixture_id: int):
    """Head-to-head team statistics (possession, shots, corners, ...) per team."""
    try:
        return fetch(
            """SELECT team_id, team_name, stat_type, stat_value
               FROM raw_af.fixture_stats WHERE fixture_id = ?""", [fixture_id])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/fixture-players")
def fixture_players(fixture_id: int):
    """Per-player match statistics ordered by minutes played."""
    try:
        return fetch(
            """SELECT team_id, team_name, player_id, player_name, number, position,
               minutes, rating, goals, assists, shots_total, shots_on,
               passes_total, passes_key, passes_accuracy, tackles, interceptions,
               duels_total, duels_won, dribbles_attempts, dribbles_success,
               fouls_drawn, fouls_committed, yellow, red
               FROM raw_af.player_stats WHERE fixture_id = ?
               ORDER BY minutes DESC NULLS LAST, rating DESC NULLS LAST""",
            [fixture_id])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/fixture-odds")
def fixture_odds(fixture_id: int, bookmaker: Optional[str] = None):
    """Pre-match odds values, optionally filtered to one bookmaker."""
    try:
        return fetch(
            """SELECT bookmaker_id, bookmaker_name, bet_id, bet_name,
               value_name, odd FROM raw_af.odds
               WHERE fixture_id = ? AND (? IS NULL OR bookmaker_name = ?)
               ORDER BY bookmaker_name, bet_id, value_name""",
            [fixture_id, bookmaker, bookmaker])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/top-scorers")
def top_scorers(league_id: Optional[int] = None, season: Optional[int] = None,
                limit: int = Query(20, le=100)):
    """Goals + assists leaders aggregated from backfilled player stats."""
    try:
        return fetch(
            """SELECT p.player_id, max(p.player_name) AS player_name,
               max(p.team_name) AS team_name, max(f.league_name) AS league_name,
               max(f.league_id) AS league_id, max(f.season) AS season,
               count(*) AS appearances,
               coalesce(sum(p.goals), 0) AS goals,
               coalesce(sum(p.assists), 0) AS assists,
               coalesce(sum(p.minutes), 0) AS minutes,
               round(avg(try_cast(p.rating AS DOUBLE)), 2) AS avg_rating
               FROM raw_af.player_stats p
               JOIN raw_af.fixtures f ON p.fixture_id = f.fixture_id
               WHERE (? IS NULL OR f.league_id = ?)
                 AND (? IS NULL OR f.season = ?)
               GROUP BY p.player_id
               ORDER BY goals DESC, assists DESC, minutes DESC LIMIT ?""",
            [league_id, league_id, season, season, limit])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/player-search")
def player_search(q: str = Query("", min_length=2), limit: int = Query(20, le=50)):
    """Distinct players by name prefix for selectors and comparison."""
    try:
        return fetch(
            """SELECT player_id, max(player_name) AS player_name,
               max(team_name) AS team_name, count(*) AS appearances
               FROM raw_af.player_stats
               WHERE lower(player_name) LIKE lower(?) || '%'
               GROUP BY player_id ORDER BY appearances DESC LIMIT ?""",
            [q, limit])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/player-season")
def player_season(player_id: int):
    """Season aggregates + per-match log for one player."""
    try:
        summary = fetch(
            """SELECT max(p.player_name) AS player_name, max(p.team_name) AS team_name,
               max(p.position) AS position, count(*) AS appearances,
               coalesce(sum(p.minutes), 0) AS minutes,
               coalesce(sum(p.goals), 0) AS goals,
               coalesce(sum(p.assists), 0) AS assists,
               coalesce(sum(p.shots_total), 0) AS shots_total,
               coalesce(sum(p.shots_on), 0) AS shots_on,
               round(avg(try_cast(p.rating AS DOUBLE)), 2) AS avg_rating,
               coalesce(sum(p.yellow), 0) AS yellow, coalesce(sum(p.red), 0) AS red
               FROM raw_af.player_stats p WHERE p.player_id = ?""", [player_id])
        if not summary or summary[0]["appearances"] == 0:
            return {"summary": None, "matches": []}
        matches = fetch(
            """SELECT p.fixture_id, f.fixture_date, f.home_team_name, f.away_team_name,
               f.goals_home, f.goals_away, p.minutes, p.rating, p.goals, p.assists,
               p.shots_total, p.shots_on, p.team_name
               FROM raw_af.player_stats p
               JOIN raw_af.fixtures f ON p.fixture_id = f.fixture_id
               WHERE p.player_id = ? ORDER BY f.fixture_date DESC""", [player_id])
        return {"summary": summary[0], "matches": matches}
    except HTTPException:
        return JSONResponse(content={"summary": None, "matches": []})


@app.get("/api/injuries")
def injuries(fixture_id: Optional[int] = None, league_id: Optional[int] = None,
             season: Optional[int] = None, team_id: Optional[int] = None):
    """Unavailable players (injury/suspension) by fixture, league or team."""
    try:
        return fetch(
            """SELECT i.player_id, i.player_name, i.injury_type, i.reason,
               i.team_id, i.team_name, i.fixture_id, i.fixture_date,
               f.league_id, f.season
               FROM raw_af.injuries i
               LEFT JOIN raw_af.fixtures f ON i.fixture_id = f.fixture_id
               WHERE (? IS NULL OR i.fixture_id = ?)
                 AND (? IS NULL OR f.league_id = ?)
                 AND (? IS NULL OR f.season = ?)
                 AND (? IS NULL OR i.team_id = ?)
               ORDER BY i.team_name, i.player_name""",
            [fixture_id, fixture_id, league_id, league_id,
             season, season, team_id, team_id])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/team-strengths")
def team_strengths(competition_id: int, season: int, team_id: Optional[int] = None):
    """Poisson-style attack/defense strengths from mart_team_strengths."""
    try:
        return fetch(
            """SELECT team_id, team_name, played, goals_for_per_game,
               goals_against_per_game, attack_strength, defense_strength,
               home_attack_strength, home_defense_strength,
               away_attack_strength, away_defense_strength
               FROM marts.mart_team_strengths
               WHERE competition_id = ? AND season = ?
                 AND (? IS NULL OR team_id = ?)""",
            [competition_id, season, team_id, team_id])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/tournament-groups")
def tournament_groups(competition_id: int, season: int):
    """Group-stage tables for a cup tournament (empty for leagues)."""
    try:
        return fetch(
            """SELECT group_name, position, team_id, team_name, played,
               goals_for, goals_against, goal_difference, points
               FROM marts.mart_tournament_groups
               WHERE competition_id = ? AND season = ?
               ORDER BY group_name, position""",
            [competition_id, season])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/knockout")
def knockout(competition_id: int, season: int):
    """Knockout-bracket fixtures ordered by round then date."""
    try:
        return fetch(
            """SELECT match_id, stage, round_order, match_date, match_datetime,
               match_status, is_completed,
               home_team_id, home_team_name, home_crest_url,
               away_team_id, away_team_name, away_crest_url,
               home_goals, away_goals
               FROM marts.mart_knockout
               WHERE competition_id = ? AND season = ?
               ORDER BY round_order, match_datetime, match_id""",
            [competition_id, season])
    except HTTPException:
        return JSONResponse(content=[])


@app.get("/api/fixture-resolve")
def fixture_resolve(fd_match_id: int):
    """Map a football-data.org match id to its API-Football fixture (or null)."""
    try:
        rows = fetch(
            """SELECT m.match_date, hm.af_team_id AS af_home, am.af_team_id AS af_away
               FROM marts.fact_matches m
               LEFT JOIN metadata.team_map hm ON m.home_team_id = hm.fd_team_id
               LEFT JOIN metadata.team_map am ON m.away_team_id = am.fd_team_id
               WHERE m.match_id = ?""", [fd_match_id])
        if not rows or rows[0]["af_home"] is None:
            return {"fixture_id": None}
        match_date = str(rows[0]["match_date"])[:10]
        found = fetch(
            """SELECT fixture_id FROM raw_af.fixtures
               WHERE home_team_id = ? AND away_team_id = ?
                 AND cast(fixture_date AS DATE)
                     BETWEEN cast(? AS DATE) - INTERVAL 1 DAY
                         AND cast(? AS DATE) + INTERVAL 1 DAY
               LIMIT 1""",
            [rows[0]["af_home"], rows[0]["af_away"], match_date, match_date])
        return {"fixture_id": found[0]["fixture_id"] if found else None}
    except HTTPException:
        return JSONResponse(content={"fixture_id": None})


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

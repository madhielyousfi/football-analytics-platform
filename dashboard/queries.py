"""Parameterized read queries over dbt marts and dimensions."""

from datetime import date

import pandas as pd
import duckdb

from dashboard.database import query_frame


def competition_seasons() -> pd.DataFrame:
    return query_frame("""SELECT DISTINCT f.competition_id, c.competition_name, f.season
        FROM marts.fact_matches AS f
        JOIN marts.dim_competition AS c USING (competition_id)
        ORDER BY c.competition_name, f.season DESC""")


def teams(competition_id: int, season: int) -> pd.DataFrame:
    return query_frame("""SELECT l.team_id, l.team_name, t.crest_url
        FROM marts.mart_league_table AS l
        LEFT JOIN marts.dim_team AS t ON l.team_id = t.team_id
        WHERE l.competition_id = ? AND l.season = ? ORDER BY l.team_name""",
        (competition_id, season))


def overview(competition_id: int, season: int) -> pd.DataFrame:
    return query_frame("""SELECT coalesce(g.matches_played, 0) AS total_matches,
        coalesce(g.total_goals, 0) AS total_goals,
        coalesce(g.average_goals_per_match, 0) AS average_goals_per_match,
        (SELECT count(*) FROM marts.mart_league_table
         WHERE competition_id = ? AND season = ?) AS number_of_teams
        FROM (SELECT 1) AS base
        LEFT JOIN marts.mart_goal_analysis AS g
          ON g.competition_id = ? AND g.season = ?""",
        (competition_id, season, competition_id, season))


def league_table(competition_id: int, season: int) -> pd.DataFrame:
    return query_frame("""SELECT l.position, l.team_id, l.team_name, t.crest_url,
        l.played, l.wins, l.draws, l.losses, l.goals_for,
        l.goals_against, l.goal_difference, l.points
        FROM marts.mart_league_table AS l
        LEFT JOIN marts.dim_team AS t ON l.team_id = t.team_id
        WHERE l.competition_id = ? AND l.season = ? ORDER BY l.position""",
        (competition_id, season))


def all_team_form(competition_id: int, season: int) -> pd.DataFrame:
    """Read recent team form already computed by dbt."""
    return query_frame("""SELECT f.team_id, t.team_name, f.recent_form,
        f.points_last_5, f.recent_matches
        FROM marts.mart_team_form AS f
        JOIN marts.dim_team AS t USING (team_id)
        WHERE f.competition_id = ? AND f.season = ?
        ORDER BY f.points_last_5 DESC, t.team_name""", (competition_id, season))


def match_outcomes(competition_id: int, season: int) -> pd.DataFrame:
    """Count completed match outcomes from dbt fact flags."""
    return query_frame("""SELECT count(*) AS total_matches,
        count(*) FILTER (WHERE is_home_win) AS home_wins,
        count(*) FILTER (WHERE is_away_win) AS away_wins,
        count(*) FILTER (WHERE is_draw) AS draws
        FROM marts.fact_matches
        WHERE competition_id = ? AND season = ? AND is_completed""",
        (competition_id, season))


def pipeline_runs(limit: int = 20) -> pd.DataFrame:
    """Read operational metadata, tolerating older databases without the table."""
    try:
        return query_frame("""SELECT run_id, pipeline_name, started_at, completed_at,
            status, rows_received, rows_inserted, rows_updated, error_message,
            date_diff('second', started_at, completed_at) AS duration_seconds
            FROM metadata.pipeline_runs
            ORDER BY started_at DESC LIMIT ?""", (limit,))
    except duckdb.CatalogException:
        return pd.DataFrame()


def team_performance(competition_id: int, season: int, team_id: int | None = None) -> pd.DataFrame:
    return query_frame("""SELECT * FROM marts.mart_team_performance
        WHERE competition_id = ? AND season = ?
          AND (? IS NULL OR team_id = ?)""",
        (competition_id, season, team_id, team_id))


def team_form(competition_id: int, season: int, team_id: int) -> pd.DataFrame:
    return query_frame("""SELECT * FROM marts.mart_team_form
        WHERE competition_id = ? AND season = ? AND team_id = ?""",
        (competition_id, season, team_id))


def home_away(competition_id: int, season: int, team_id: int | None = None) -> pd.DataFrame:
    return query_frame("""SELECT h.*, t.team_name FROM marts.mart_home_away AS h
        JOIN marts.dim_team AS t USING (team_id)
        WHERE h.competition_id = ? AND h.season = ?
          AND (? IS NULL OR h.team_id = ?)""",
        (competition_id, season, team_id, team_id))


def goal_trends(competition_id: int, season: int) -> pd.DataFrame:
    return query_frame("""SELECT match_date, matches_played, goals, home_goals, away_goals,
        round(goals::DOUBLE / nullif(matches_played, 0), 2) AS average_goals
        FROM marts.mart_goal_trends
        WHERE competition_id = ? AND season = ? ORDER BY match_date""",
        (competition_id, season))


def team_progression(competition_id: int, season: int, team_id: int) -> pd.DataFrame:
    return query_frame("""SELECT match_id, match_date, match_datetime, opponent_name,
        venue_type, result, goals_for, goals_against, points,
        cumulative_goals, cumulative_points
        FROM marts.mart_team_progression
        WHERE competition_id = ? AND season = ? AND team_id = ?
        ORDER BY match_datetime, match_id""", (competition_id, season, team_id))


def match_filter_options(competition_id: int, season: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = query_frame("""SELECT min(match_date) AS min_date, max(match_date) AS max_date
        FROM marts.fact_matches WHERE competition_id = ? AND season = ?""", (competition_id, season))
    matchdays = query_frame("""SELECT DISTINCT matchday FROM marts.fact_matches
        WHERE competition_id = ? AND season = ? AND matchday IS NOT NULL
        ORDER BY matchday""", (competition_id, season))
    statuses = query_frame("""SELECT DISTINCT match_status FROM marts.fact_matches
        WHERE competition_id = ? AND season = ? ORDER BY match_status""", (competition_id, season))
    return dates, matchdays, statuses


def matches(competition_id: int, season: int, team_id: int | None,
            matchday: int | None, start_date: date, end_date: date,
            status: str | None) -> pd.DataFrame:
    return query_frame("""SELECT f.match_id, f.match_date, home.team_name AS home_team,
        home.crest_url AS home_crest_url, away.team_name AS away_team,
        away.crest_url AS away_crest_url, f.home_goals, f.away_goals,
        f.match_status, f.matchday
        FROM marts.fact_matches AS f
        JOIN marts.dim_team AS home ON f.home_team_id = home.team_id
        JOIN marts.dim_team AS away ON f.away_team_id = away.team_id
        WHERE f.competition_id = ? AND f.season = ?
          AND (? IS NULL OR f.home_team_id = ? OR f.away_team_id = ?)
          AND (? IS NULL OR f.matchday = ?)
          AND f.match_date BETWEEN ? AND ?
          AND (? IS NULL OR f.match_status = ?)
        ORDER BY f.match_date DESC, f.match_id DESC""",
        (competition_id, season, team_id, team_id, team_id,
         matchday, matchday, start_date, end_date, status, status))


def league_comparison(competition_id: int, season: int) -> pd.DataFrame:
    return query_frame("""SELECT l.position, l.team_id, l.team_name, l.points,
        l.goals_for, l.goals_against, l.goal_difference,
        p.win_percentage, h.home_wins, h.away_wins,
        h.home_win_rate, h.away_win_rate
        FROM marts.mart_league_table AS l
        LEFT JOIN marts.mart_team_performance AS p
          ON l.competition_id = p.competition_id
          AND l.season = p.season AND l.team_id = p.team_id
        LEFT JOIN marts.mart_home_away AS h
          ON l.competition_id = h.competition_id
          AND l.season = h.season AND l.team_id = h.team_id
        WHERE l.competition_id = ? AND l.season = ?
        ORDER BY l.position""", (competition_id, season))


def head_to_head(competition_id: int, season: int, team_a_id: int,
                 team_b_id: int) -> pd.DataFrame:
    return query_frame("""SELECT matches_played, draws, recent_results,
        CASE WHEN team_a_id = ? THEN team_a_wins ELSE team_b_wins END AS selected_a_wins,
        CASE WHEN team_a_id = ? THEN team_b_wins ELSE team_a_wins END AS selected_b_wins,
        CASE WHEN team_a_id = ? THEN team_a_goals ELSE team_b_goals END AS selected_a_goals,
        CASE WHEN team_a_id = ? THEN team_b_goals ELSE team_a_goals END AS selected_b_goals
        FROM marts.mart_head_to_head
        WHERE competition_id = ? AND season = ?
          AND team_a_id = least(?, ?) AND team_b_id = greatest(?, ?)""",
        (team_a_id, team_a_id, team_a_id, team_a_id,
         competition_id, season, team_a_id, team_b_id, team_a_id, team_b_id))


def head_to_head_matches(competition_id: int, season: int, team_a_id: int,
                         team_b_id: int) -> pd.DataFrame:
    return query_frame("""SELECT f.match_date, home.team_name AS home_team,
        away.team_name AS away_team, f.home_goals, f.away_goals
        FROM marts.fact_matches AS f
        JOIN marts.dim_team AS home ON f.home_team_id = home.team_id
        JOIN marts.dim_team AS away ON f.away_team_id = away.team_id
        WHERE f.competition_id = ? AND f.season = ? AND f.is_completed
          AND ((f.home_team_id = ? AND f.away_team_id = ?)
            OR (f.home_team_id = ? AND f.away_team_id = ?))
        ORDER BY f.match_date DESC, f.match_id DESC LIMIT 10""",
        (competition_id, season, team_a_id, team_b_id, team_b_id, team_a_id))

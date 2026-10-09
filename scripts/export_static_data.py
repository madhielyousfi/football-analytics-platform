"""Export a static JSON snapshot of the dbt marts for the GitHub Pages demo.

GitHub Pages serves static files only (no FastAPI/DuckDB), so this script
dumps every dataset the Next.js frontend needs into frontend/public/data/.
The frontend's static mode (NEXT_PUBLIC_DATA_MODE=static) reads these files
instead of calling the API.

Usage:
    python scripts/export_static_data.py --db data/demo.duckdb --out frontend/public/data

Only dependency: duckdb.
"""

from __future__ import annotations

import argparse
import json
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import duckdb


def serialize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def fetch(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> list[dict]:
    rel = con.execute(sql, params or [])
    cols = [d[0] for d in rel.description]
    return [{k: serialize(v) for k, v in zip(cols, row)} for row in rel.fetchall()]


def write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Path to DuckDB file with built marts")
    ap.add_argument("--out", required=True, help="Output dir (frontend/public/data)")
    args = ap.parse_args()

    out = Path(args.out)
    with closing(duckdb.connect(str(args.db), read_only=True)) as con:
        comps = fetch(
            con,
            """SELECT DISTINCT f.competition_id, c.competition_name, c.competition_code,
               c.competition_type, f.season
               FROM marts.fact_matches f JOIN marts.dim_competition c USING (competition_id)
               ORDER BY c.competition_name, f.season DESC""",
        )
        grouped: dict[int, dict] = {}
        for r in comps:
            cid = r["competition_id"]
            grouped.setdefault(cid, {"competition_id": cid, "competition_name": r["competition_name"],
                                     "competition_code": r.get("competition_code"),
                                     "competition_type": r.get("competition_type"), "seasons": []})
            grouped[cid]["seasons"].append(r["season"])
        write(out / "competitions.json", list(grouped.values()))

        try:
            runs = fetch(
                con,
                """SELECT run_id, pipeline_name, started_at, completed_at, status,
                   rows_received, rows_inserted, rows_updated, error_message,
                   date_diff('second', started_at, completed_at) AS duration_seconds
                   FROM metadata.pipeline_runs ORDER BY started_at DESC LIMIT 20""",
            )
        except duckdb.CatalogException:
            runs = []
        write(out / "pipeline-runs.json", runs)

        try:
            live = fetch(
                con,
                """SELECT fixture_id, league_id, league_name, season, round, fixture_date,
                   status_long, status_short, elapsed,
                   home_team_id, home_team_name, NULL AS home_crest_url,
                   away_team_id, away_team_name, NULL AS away_crest_url,
                   goals_home, goals_away
                   FROM raw_af.fixtures
                   ORDER BY CASE WHEN status_short IN
                     ('1H','HT','2H','ET','BT','P','SUSP','INT','LIVE') THEN 0
                     WHEN fixture_date >= current_date THEN 1 ELSE 2 END,
                     CASE WHEN status_short IN
                       ('1H','HT','2H','ET','BT','P','SUSP','INT','LIVE')
                       OR fixture_date >= current_date
                       THEN fixture_date END ASC NULLS LAST,
                     fixture_date DESC LIMIT 100""",
            )
        except duckdb.CatalogException:
            live = []
        write(out / "live.json", live)

        try:
            af_fixtures = fetch(
                con,
                """SELECT fixture_id, league_id, league_name, season, round, fixture_date,
                   status_long, status_short, elapsed,
                   home_team_id, home_team_name, NULL AS home_crest_url,
                   away_team_id, away_team_name, NULL AS away_crest_url,
                   goals_home, goals_away
                   FROM raw_af.fixtures ORDER BY fixture_date DESC LIMIT 1000""",
            )
            af_events = fetch(
                con,
                """SELECT fixture_id, elapsed, extra_minute, team_id, team_name,
                   player_id, player_name, assist_player_id, assist_player_name,
                   event_type, detail, comments
                   FROM raw_af.events ORDER BY fixture_id, elapsed LIMIT 20000""",
            )
            resolve_rows = fetch(
                con,
                """SELECT m.match_id AS fd_match_id, f.fixture_id AS fixture_id
                   FROM marts.fact_matches m
                   JOIN metadata.team_map hm ON m.home_team_id = hm.fd_team_id
                   JOIN metadata.team_map am ON m.away_team_id = am.fd_team_id
                   JOIN raw_af.fixtures f
                     ON f.home_team_id = hm.af_team_id
                     AND f.away_team_id = am.af_team_id
                     AND cast(f.fixture_date AS DATE)
                         BETWEEN m.match_date - INTERVAL 1 DAY
                             AND m.match_date + INTERVAL 1 DAY""",
            )
        except duckdb.CatalogException:
            af_fixtures, af_events, resolve_rows = [], [], []
        write(out / "af-fixtures.json", af_fixtures)
        write(out / "af-events.json", af_events)
        write(out / "af-resolve.json",
              {str(r["fd_match_id"]): r["fixture_id"] for r in resolve_rows})
        try:
            write(out / "fd-matches.json", fetch(
                con,
                """SELECT f.match_id, f.match_date, f.match_status, f.matchday,
                   f.competition_id, f.season, c.competition_name,
                   f.home_team_id, home.team_name AS home_team,
                   home.crest_url AS home_crest_url,
                   f.away_team_id, away.team_name AS away_team,
                   away.crest_url AS away_crest_url,
                   f.home_goals, f.away_goals
                   FROM marts.fact_matches f
                   JOIN marts.dim_competition c USING (competition_id)
                   JOIN marts.dim_team home ON f.home_team_id = home.team_id
                   JOIN marts.dim_team away ON f.away_team_id = away.team_id
                   LIMIT 3000"""))
        except duckdb.CatalogException:
            write(out / "fd-matches.json", [])
        try:
            write(out / "af-lineups.json", fetch(
                con,
                """SELECT fixture_id, team_id, team_name, formation, coach_name,
                   player_id, player_name, number, position, grid, is_starting
                   FROM raw_af.lineups LIMIT 20000"""))
            write(out / "af-fixture-stats.json", fetch(
                con,
                """SELECT fixture_id, team_id, team_name, stat_type, stat_value
                   FROM raw_af.fixture_stats LIMIT 20000"""))
            write(out / "af-player-stats.json", fetch(
                con,
                """SELECT fixture_id, team_id, team_name, player_id, player_name,
                   number, position, minutes, rating, goals, assists, shots_total,
                   shots_on, passes_total, passes_key, passes_accuracy, tackles,
                   interceptions, duels_total, duels_won, dribbles_attempts,
                   dribbles_success, fouls_drawn, fouls_committed, yellow, red
                   FROM raw_af.player_stats LIMIT 20000"""))
            write(out / "af-odds.json", fetch(
                con,
                """SELECT fixture_id, bookmaker_id, bookmaker_name, bet_id,
                   bet_name, value_name, odd FROM raw_af.odds LIMIT 20000"""))
        except duckdb.CatalogException:
            for name in ("af-lineups.json", "af-fixture-stats.json",
                         "af-player-stats.json", "af-odds.json"):
                write(out / name, [])
        try:
            write(out / "af-injuries.json", fetch(
                con,
                """SELECT i.player_id, i.player_name, i.injury_type, i.reason,
                   i.team_id, i.team_name, i.fixture_id, i.fixture_date,
                   f.league_id, f.season
                   FROM raw_af.injuries i
                   LEFT JOIN raw_af.fixtures f ON i.fixture_id = f.fixture_id
                   LIMIT 5000"""))
        except duckdb.CatalogException:
            write(out / "af-injuries.json", [])
        try:
            write(out / "strengths.json", fetch(
                con,
                """SELECT competition_id, season, team_id, team_name, played,
                   goals_for_per_game, goals_against_per_game,
                   attack_strength, defense_strength,
                   home_attack_strength, home_defense_strength,
                   away_attack_strength, away_defense_strength
                   FROM marts.mart_team_strengths"""))
            write(out / "goal-averages.json", fetch(
                con,
                """SELECT competition_id, season, average_home_goals,
                   average_away_goals, average_goals_per_match
                   FROM marts.mart_goal_analysis"""))
        except duckdb.CatalogException:
            write(out / "strengths.json", [])
            write(out / "goal-averages.json", [])
        try:
            write(out / "af-top-scorers.json", fetch(
                con,
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
                   GROUP BY p.player_id
                   ORDER BY goals DESC, assists DESC LIMIT 500"""))
            write(out / "af-players.json", fetch(
                con,
                """SELECT player_id, max(player_name) AS player_name,
                   max(team_name) AS team_name, count(*) AS appearances
                   FROM raw_af.player_stats
                   GROUP BY player_id ORDER BY appearances DESC LIMIT 5000"""))
            write(out / "af-player-matches.json", fetch(
                con,
                """SELECT p.player_id, p.player_name, p.fixture_id, f.fixture_date,
                   f.home_team_name, f.away_team_name, f.goals_home, f.goals_away,
                   p.team_name, p.minutes, p.rating, p.goals, p.assists,
                   p.shots_total, p.shots_on
                   FROM raw_af.player_stats p
                   JOIN raw_af.fixtures f ON p.fixture_id = f.fixture_id
                   ORDER BY f.fixture_date DESC LIMIT 20000"""))
        except duckdb.CatalogException:
            for name in ("af-top-scorers.json", "af-players.json",
                         "af-player-matches.json"):
                write(out / name, [])

        pairs = {(r["competition_id"], r["season"]) for r in comps}
        for cid, season in sorted(pairs):
            cs = out / f"c{cid}_s{season}"
            p = [cid, season]

            write(cs / "overview.json", fetch(
                con,
                """SELECT coalesce(g.matches_played,0) AS total_matches, coalesce(g.total_goals,0) AS total_goals,
                   coalesce(g.average_goals_per_match,0) AS average_goals_per_match,
                   (SELECT count(*) FROM marts.mart_league_table WHERE competition_id=? AND season=?) AS number_of_teams,
                   g.matches_over_2_5, g.matches_under_2_5, g.scoreless_draws,
                   g.average_home_goals, g.average_away_goals
                   FROM (SELECT 1) base LEFT JOIN marts.mart_goal_analysis g
                   ON g.competition_id=? AND g.season=?""",
                [cid, season, cid, season])[0])

            write(cs / "outcomes.json", fetch(
                con,
                """SELECT count(*) AS total_matches,
                   count(*) FILTER (WHERE is_home_win) AS home_wins,
                   count(*) FILTER (WHERE is_away_win) AS away_wins,
                   count(*) FILTER (WHERE is_draw) AS draws
                   FROM marts.fact_matches WHERE competition_id=? AND season=? AND is_completed""", p)[0])

            league = fetch(
                con,
                """SELECT l.position, l.team_id, l.team_name, t.crest_url, t.short_name,
                   l.played, l.wins, l.draws, l.losses, l.goals_for, l.goals_against, l.goal_difference, l.points
                   FROM marts.mart_league_table l LEFT JOIN marts.dim_team t ON l.team_id=t.team_id
                   WHERE l.competition_id=? AND l.season=? ORDER BY l.position""", p)
            write(cs / "league-table.json", league)

            try:
                groups = fetch(
                    con,
                    """SELECT group_name, position, team_id, team_name, played,
                       goals_for, goals_against, goal_difference, points
                       FROM marts.mart_tournament_groups
                       WHERE competition_id = ? AND season = ?
                       ORDER BY group_name, position""", p)
                bracket = fetch(
                    con,
                    """SELECT match_id, stage, round_order, match_date, match_datetime,
                       match_status, is_completed,
                       home_team_id, home_team_name, home_crest_url,
                       away_team_id, away_team_name, away_crest_url,
                       home_goals, away_goals
                       FROM marts.mart_knockout
                       WHERE competition_id = ? AND season = ?
                       ORDER BY round_order, match_datetime, match_id""", p)
            except duckdb.CatalogException:
                groups, bracket = [], []
            write(cs / "tournament-groups.json", groups)
            write(cs / "knockout.json", bracket)

            write(cs / "league-comparison.json", fetch(
                con,
                """SELECT l.position, l.team_id, l.team_name, l.points, l.goals_for, l.goals_against, l.goal_difference,
                   p.win_percentage, h.home_wins, h.away_wins, h.home_win_rate, h.away_win_rate
                   FROM marts.mart_league_table l
                   LEFT JOIN marts.mart_team_performance p ON l.competition_id=p.competition_id AND l.season=p.season AND l.team_id=p.team_id
                   LEFT JOIN marts.mart_home_away h ON l.competition_id=h.competition_id AND l.season=h.season AND l.team_id=h.team_id
                   WHERE l.competition_id=? AND l.season=? ORDER BY l.position""", p))

            form = fetch(
                con,
                """SELECT f.team_id, t.team_name, t.crest_url, f.recent_form, f.points_last_5, f.recent_matches
                   FROM marts.mart_team_form f JOIN marts.dim_team t USING (team_id)
                   WHERE f.competition_id=? AND f.season=? ORDER BY f.points_last_5 DESC, t.team_name""", p)
            write(cs / "all-team-form.json", form)

            perf = fetch(con, "SELECT * FROM marts.mart_team_performance WHERE competition_id=? AND season=?", p)
            write(cs / "team-performance.json", perf)

            ha = fetch(
                con,
                """SELECT h.*, t.team_name FROM marts.mart_home_away h JOIN marts.dim_team t USING (team_id)
                   WHERE h.competition_id=? AND h.season=?""", p)
            write(cs / "home-away.json", ha)

            write(cs / "goal-trends.json", fetch(
                con,
                """SELECT match_date, matches_played, goals, home_goals, away_goals,
                   round(goals::DOUBLE / nullif(matches_played,0),2) AS average_goals
                   FROM marts.mart_goal_trends WHERE competition_id=? AND season=? ORDER BY match_date""", p))

            dates = fetch(con, "SELECT min(match_date) AS min_date, max(match_date) AS max_date FROM marts.fact_matches WHERE competition_id=? AND season=?", p)
            matchdays = fetch(con, "SELECT DISTINCT matchday FROM marts.fact_matches WHERE competition_id=? AND season=? AND matchday IS NOT NULL ORDER BY matchday", p)
            statuses = fetch(con, "SELECT DISTINCT match_status FROM marts.fact_matches WHERE competition_id=? AND season=? ORDER BY match_status", p)
            write(cs / "match-options.json", {"dates": dates[0] if dates else {},
                                              "matchdays": [r["matchday"] for r in matchdays],
                                              "statuses": [r["match_status"] for r in statuses]})

            matches = fetch(
                con,
                """SELECT f.match_id, f.match_date, home.team_name AS home_team, home.crest_url AS home_crest_url,
                   home.team_id AS home_team_id, away.team_name AS away_team, away.crest_url AS away_crest_url,
                   away.team_id AS away_team_id, f.home_goals, f.away_goals, f.match_status, f.matchday
                   FROM marts.fact_matches f
                   JOIN marts.dim_team home ON f.home_team_id=home.team_id
                   JOIN marts.dim_team away ON f.away_team_id=away.team_id
                   WHERE f.competition_id=? AND f.season=?
                   ORDER BY f.match_date DESC, f.match_id DESC""", p)
            write(cs / "matches.json", matches)

            form_by_team = {f["team_id"]: f for f in form}
            perf_by_team: dict[int, list] = {}
            for row in perf:
                perf_by_team.setdefault(row["team_id"], []).append(row)
            ha_by_team: dict[int, list] = {}
            for row in ha:
                ha_by_team.setdefault(row["team_id"], []).append(row)
            for t in league:
                tid = t["team_id"]
                prog = fetch(
                    con,
                    """SELECT match_id, match_date, match_datetime, opponent_name, venue_type, result,
                       goals_for, goals_against, points, cumulative_goals, cumulative_points
                       FROM marts.mart_team_progression
                       WHERE competition_id=? AND season=? AND team_id=? ORDER BY match_datetime, match_id""",
                    [cid, season, tid])
                write(cs / "teams" / f"{tid}.json", {
                    "form": form_by_team.get(tid, {}),
                    "performance": perf_by_team.get(tid, []),
                    "homeAway": ha_by_team.get(tid, []),
                    "progression": prog,
                })

            team_ids = [t["team_id"] for t in league]
            for i, a in enumerate(team_ids):
                for b in team_ids[i + 1:]:
                    lo, hi = min(a, b), max(a, b)
                    summary = fetch(
                        con,
                        """SELECT matches_played, draws, recent_results,
                           CASE WHEN team_a_id=? THEN team_a_wins ELSE team_b_wins END AS selected_a_wins,
                           CASE WHEN team_a_id=? THEN team_b_wins ELSE team_a_wins END AS selected_b_wins,
                           CASE WHEN team_a_id=? THEN team_a_goals ELSE team_b_goals END AS selected_a_goals,
                           CASE WHEN team_a_id=? THEN team_b_goals ELSE team_a_goals END AS selected_b_goals
                           FROM marts.mart_head_to_head WHERE competition_id=? AND season=?
                           AND team_a_id=? AND team_b_id=?""",
                        [a, a, a, a, cid, season, lo, hi])
                    if not summary:
                        continue
                    games = fetch(
                        con,
                        """SELECT f.match_date, home.team_name AS home_team, away.team_name AS away_team,
                           f.home_goals, f.away_goals FROM marts.fact_matches f
                           JOIN marts.dim_team home ON f.home_team_id=home.team_id
                           JOIN marts.dim_team away ON f.away_team_id=away.team_id
                           WHERE f.competition_id=? AND f.season=? AND f.is_completed
                           AND ((f.home_team_id=? AND f.away_team_id=?) OR (f.home_team_id=? AND f.away_team_id=?))
                           ORDER BY f.match_date DESC, f.match_id DESC LIMIT 10""",
                        [cid, season, a, b, b, a])
                    write(cs / "h2h" / f"{lo}_{hi}.json", {"summary": summary[0], "matches": games})

    files = sum(1 for _ in out.rglob("*.json"))
    print(f"Exported {len(pairs)} competition-seasons, {files} JSON files -> {out}")


if __name__ == "__main__":
    main()

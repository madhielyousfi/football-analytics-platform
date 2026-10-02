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
            """SELECT DISTINCT f.competition_id, c.competition_name, c.competition_code, f.season
               FROM marts.fact_matches f JOIN marts.dim_competition c USING (competition_id)
               ORDER BY c.competition_name, f.season DESC""",
        )
        grouped: dict[int, dict] = {}
        for r in comps:
            cid = r["competition_id"]
            grouped.setdefault(cid, {"competition_id": cid, "competition_name": r["competition_name"],
                                     "competition_code": r.get("competition_code"), "seasons": []})
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
                   WHERE status_short IN ('1H','HT','2H','ET','BT','P','SUSP','INT','LIVE')
                      OR fixture_date >= current_date - INTERVAL 1 DAY
                   ORDER BY CASE WHEN status_short IN
                     ('1H','HT','2H','ET','BT','P','SUSP','INT','LIVE') THEN 0 ELSE 1 END,
                     fixture_date LIMIT 100""",
            )
        except duckdb.CatalogException:
            live = []
        write(out / "live.json", live)

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

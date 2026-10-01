# Data dictionary and quality rules

## Raw and staging

| Raw table | Business key | Staging view | Notes |
| --- | --- | --- | --- |
| `raw.competitions` | `competition_id` | `stg_competitions` | One row per competition. The JSON payload retains API fields not yet modeled. |
| `raw.teams` | `team_id` | `stg_teams` | Latest ingested team attributes; `_season` and `competition_id` identify that load. |
| `raw.matches` | `match_id` | `stg_matches` | Includes played and scheduled matches; reruns update status and scores. |
| `raw.standings` | `standing_key` | `stg_standings` | Key includes competition, season, standing type, stage, group and team. Official TOTAL, HOME and AWAY tables stay distinct. |

Every raw table has `_payload`, `_ingested_at`, `_batch_id`, `_source` and `_api_endpoint`; match, team and standing rows also carry `_season`, and matches and standings carry `_competition`. `metadata.pipeline_runs` has one row per execution, with RUNNING, SUCCESS or FAILED status and row counters.

## Intermediate and star models

| Model | Grain | Main rules |
| --- | --- | --- |
| `int_match_results` | Match ID | Scores, points, goal difference, winner and result flags exist only for `FINISHED` matches with both scores. |
| `int_team_matches` | Match ID × team ID | Two rows per completed match. Home and away views use the same match result. |
| `dim_team` | Team ID | Most recent team attributes, with a match-name fallback. |
| `dim_competition` | Competition ID | Current competition metadata and season dates. |
| `dim_date` | UTC calendar date | Continuous dates between earliest and latest loaded match; integer `YYYYMMDD` key. |
| `fact_matches` | Match ID | One row per match; foreign keys to date, competition and both teams. |

Win = 3 points, draw = 1, loss = 0. A scheduled or timed fixture contributes no completed-match measures. `match_date` and `date_id` use UTC even when the local machine displays timestamps in another timezone.

## Analytical marts

| Mart | Grain | Definition |
| --- | --- | --- |
| `mart_team_performance` | Team × competition × season | Completed W/D/L, goals, points and rates. |
| `mart_league_table` | Team × competition × season | Participants ranked by points, goal difference and goals for, then stable name and ID. Includes teams with zero played matches. |
| `mart_team_form` | Team × competition × season | Latest five completed results, newest first. `form_score = points_last_5 / 15`. |
| `mart_home_away` | Team × competition × season | Home/away counts, goals and win rates. |
| `mart_goal_analysis` | Competition × season | Completed-match goal averages, over/under 2.5 counts and highest scoring match. |
| `mart_goal_trends` | UTC match date × competition × season | Daily completed-match goal totals. |
| `mart_team_progression` | Team × completed match | Cumulative points and goals in match time order. |
| `mart_head_to_head` | Unordered pair × competition × season | The lower team ID is Team A. The five latest scorelines use that perspective. |

`mart_league_table` is an analytical approximation. Competition-specific tie-breakers, point deductions and official rulings are not applied. `stg_standings` contains the API's official table for comparison; it is not substituted for the calculated mart.

## Tests

dbt checks unique and non-null model keys, fact-to-dimension relationships, accepted team result and venue values, exactly two team rows per completed match, mart business-key grain, and agreement between fact and team-performance totals for matches, goals and points. Python tests check API handling, run tracking, full and rolling-window behavior, upserts and failure recording. CI creates a token-free API-shaped fixture and runs the full dbt build.

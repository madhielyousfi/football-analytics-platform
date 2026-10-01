# football-analytics-platform

An end-to-end, local-first data engineering portfolio project. It extracts changing football data from [football-data.org API v4](https://docs.football-data.org/general/v4/competition.html), keeps source records in DuckDB, transforms them with dbt SQL, and serves tested analytics through Streamlit and Plotly.

## Business problem

API match records evolve as fixtures are rescheduled and results arrive. Direct API responses are nested and not shaped for league analysis. This platform creates repeatable ingestion, a clear one-row-per-match fact, reusable team-level metrics, and a dashboard driven by tested marts.

**Stack:** Python 3.12+, requests, DuckDB, dbt-core, dbt-duckdb, pandas, Streamlit, Plotly, pytest, GitHub Actions.

## Architecture

```text
football-data.org API v4
          ↓
Python API client and ingestion
          ↓
DuckDB raw.competitions / raw.teams / raw.matches / raw.standings
          ↓
dbt staging.stg_competitions / stg_teams / stg_matches / stg_standings
          ↓
dbt intermediate.int_match_results / int_team_matches
          ↓
dbt marts.dim_team / dim_competition / dim_date / fact_matches
          ↓
dbt marts.mart_team_performance / mart_league_table / mart_team_form
          ↓
dbt marts.mart_home_away / mart_goal_analysis / mart_head_to_head
          ↓
Streamlit + Plotly dashboard
```

The raw tables keep the original object in `_payload` as JSON, plus typed fields used by dbt. Their grain is one row per API competition, team, or match ID, or per standing type/group/team. A rerun updates an existing key, so fixture changes and match results replace earlier values. Each run records received, inserted, and updated counts in `metadata.pipeline_runs`. The four raw tables commit together; a failed run is recorded separately.

Staging views rename fields, standardize strings, cast dates and IDs, and choose the latest row per business key. SQL tests check uniqueness, required keys, and relationships between matches, teams, and competitions. They do not impose a fixed match-status list, since the API can add valid statuses. See the [architecture and lineage](docs/architecture.md), [data dictionary](docs/data_dictionary.md), and [portfolio case study](docs/portfolio_case_study.md).

## Repository structure

```text
ingestion/              API client, configuration, raw loaders, run orchestration
football_dbt/           staging, intermediate, dimensions, facts, marts, dbt tests
dashboard/              cached DuckDB queries and five Streamlit pages
scripts/                token-free CI database fixture
tests/                  offline Python tests
.github/workflows/       CI and scheduled pipeline
docs/                   architecture, data dictionary, portfolio case study
data/                   local DuckDB file (ignored by Git)
```

## Local setup

Use Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `FOOTBALL_API_TOKEN` in `.env` using a football-data.org token. Set `FOOTBALL_COMPETITION` to a competition code your API plan can access and `FOOTBALL_SEASON` to the season's starting year. The default is `PL` and `2026`; the API may reject a season that is not available to your account. `DUCKDB_PATH` defaults to `data/football.duckdb`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `FOOTBALL_API_TOKEN` | Required | API credential; keep it in `.env` or GitHub Secrets. |
| `FOOTBALL_API_BASE_URL` | API v4 URL | API root. |
| `FOOTBALL_COMPETITION` | `PL` | Competition code. |
| `FOOTBALL_SEASON` | `2026` | Season starting year. |
| `DUCKDB_PATH` | `data/football.duckdb` | Local warehouse file. |
| `FOOTBALL_REFRESH_DAYS_BACK` | `3` | Days before today included on repeat local runs. |
| `FOOTBALL_REFRESH_DAYS_FORWARD` | `7` | Days after today included on repeat local runs. |
| `FOOTBALL_FULL_REFRESH` | `false` | Set to `true` for a full season reload. |
| `FOOTBALL_API_TIMEOUT` | `30` | HTTP timeout in seconds. |
| `FOOTBALL_API_MAX_RETRIES` | `3` | Retries for transient errors. |

```bash
python -m ingestion.run_ingestion
```

The first run for a competition and season loads all matches. Later local runs request a UTC window from today minus three days through today plus seven days by default. Configure that window in `.env`; set `FOOTBALL_FULL_REFRESH=true` to re-read the full season. `dateTo` is exclusive in the API, so the request adds one day to include the configured end date. Competition, team and official standing records refresh every run. Match and standing keys make repeat loads idempotent.

## Build the dbt models

```bash
cd football_dbt
../.venv/bin/dbt debug --profiles-dir .
../.venv/bin/dbt build --profiles-dir .
cd ..
```

The committed `football_dbt/profiles.yml` contains no credentials. Its `../data/football.duckdb` path is used when dbt runs **from the `football_dbt` directory**, as in the commands above and the Makefile. Use `profiles.yml.example` as a starting point if you need a different local path. Run Python ingestion first; dbt needs the four raw source tables. `dbt build` runs both models and tests, so a separate `dbt test` is optional.

For an isolated database, set `DBT_DUCKDB_PATH` to an **absolute** path before running dbt. CI uses this to avoid touching any local warehouse.

Match lineage: `football-data.org → raw.matches → staging.stg_matches → intermediate.int_match_results → marts.fact_matches → marts.mart_goal_analysis`. The team-centric branch is `int_match_results → int_team_matches → marts.mart_team_performance → marts.mart_league_table`. Official table lineage is `API standings → raw.standings → staging.stg_standings`.

## Data model

| Model | Grain | Purpose |
| --- | --- | --- |
| `intermediate.int_match_results` | One row per match | Calculates result metrics only for `FINISHED` matches with both full-time scores. |
| `intermediate.int_team_matches` | One row per team per completed match | Provides home and away results, goals and points; exactly two rows per completed match. |
| `marts.dim_team` | One row per team ID | Team attributes, with match-name fallback for teams absent from the latest team API response. |
| `marts.dim_competition` | One row per competition ID | Competition identity and currently reported season. |
| `marts.dim_date` | One row per calendar date | Covers every date from the earliest to latest loaded match; `date_id` is `YYYYMMDD`. |
| `marts.fact_matches` | **One row per match** | Foreign keys to date, competition, and both teams, plus score and result metrics. |

Unfinished fixtures remain in `fact_matches`, but points, total goals, winner, and result flags are null until the API reports a finished match with scores. `match_date` and `date_id` use the UTC date. Competition season attributes represent the current season reported by the API; historical season analysis should use the fact's `season` and `season_id` columns. dbt builds dimensions and facts as tables, so rerun `dbt build` after every ingestion to refresh them. Tests cover keys, references, and the two-team-row rule.

## Analytical marts

| Mart | Grain | Main outputs |
| --- | --- | --- |
| `mart_team_performance` | Team × competition × season | Played, W/D/L, goals, points, per-game rates. |
| `mart_league_table` | Participant × competition × season | Standings with a position, including teams yet to play. |
| `mart_team_form` | Team × competition × season | Up to five latest completed results, points and normalized form score. |
| `mart_home_away` | Team × competition × season | Separate home and away results, goals and win rates. |
| `mart_goal_analysis` | Competition × season | Goal averages, over/under 2.5 counts, scoreless draws and highest-scoring match. |
| `mart_head_to_head` | Unordered team pair × competition × season | Wins, draws, goals and up to five recent scorelines. |
| `mart_goal_trends` | Played date × competition × season | Daily goals for the overview chart. |
| `mart_team_progression` | Completed match × team | Cumulative points and goals for team charts and recent matches. |

`mart_league_table` sorts by points, goal difference and goals for, then team name and ID for a stable order. It is a **simplified analytical table**: competition-specific head-to-head, disciplinary, or other tie-break rules are not applied. `mart_team_form.recent_form` is newest first and `form_score = points_last_5 / 15`, so teams with fewer than five games cannot yet reach the same maximum. `mart_head_to_head` always treats the lower team ID as Team A; recent scorelines are from that team's perspective. Team-level goal totals are in `mart_team_performance`.

`stg_standings` retains the API's official TOTAL, HOME and AWAY rows. The dashboard uses the calculated `mart_league_table`, so differences caused by official deductions or competition-specific rules are possible. See [data dictionary](docs/data_dictionary.md) for model grains and definitions.

The dbt tests also check each mart's business-key grain and reconcile aggregate team matches, goals, and points against `fact_matches`.

## Dashboard

Run ingestion and `dbt build` first, then from the repository root:

```bash
streamlit run dashboard/app.py
```

The sidebar selects a competition and season. The five pages are **Overview** (KPIs, table, offense, defense, goal trends), **Teams** (results, form, home/away, goals and points progression), **Matches** (team, matchday, date and status filters), **League** (standings and comparison charts), and **Head to Head** (two-team metrics and recent meetings). The app opens DuckDB read-only and queries dbt marts using parameterized SQL. It caches query results for five minutes; use **Refresh data** in the sidebar after a new build. The dashboard needs no API token if the DuckDB file already contains built marts.

Screenshot placeholders and capture guidance are in [docs/screenshots](docs/screenshots/README.md). No unverified dashboard images are included.

## Makefile and automation

```bash
make install
make ingest
make dbt-build
make dashboard
make test
make pipeline
```

`make pipeline` performs ingestion followed by `dbt build`. That dbt command includes data tests, so it does not run `dbt test` again. `make dbt-run` and `make dbt-test` are available for narrower checks.

The [CI workflow](.github/workflows/ci.yml) runs on pushes and pull requests. It installs dependencies, runs pytest, creates a tiny API-shaped DuckDB fixture without a token, and runs `dbt parse`, `dbt compile`, and `dbt build` against that fixture. To reproduce the dbt portion without touching `data/football.duckdb`:

```bash
python -m scripts.create_ci_database --db-path /tmp/football-ci.duckdb
cd football_dbt
DBT_DUCKDB_PATH=/tmp/football-ci.duckdb dbt build --profiles-dir .
cd ..
```

The [pipeline workflow](.github/workflows/pipeline.yml) runs daily at 05:17 UTC or manually. Set repository secret `FOOTBALL_API_TOKEN` before using it. Its manual inputs select a competition and season; scheduled runs use repository variables `FOOTBALL_COMPETITION` and `FOOTBALL_SEASON` if set, otherwise `PL` and `2026`. Update the season variable when a new season begins. The workflow runs pytest, ingestion, and `dbt build`, then uploads `data/football.duckdb` as a **14-day workflow artifact**.

GitHub-hosted runners are ephemeral. The scheduled workflow starts from a fresh database each day, so it performs a full season load despite the local runner's incremental support. Its database does **not** persist on the runner and does not automatically update a local dashboard. Download the successful run's `football-analytics-<run id>` artifact from the Actions page, extract `football.duckdb` into `data/`, and run the dashboard against it. Artifact retention is for demonstrations; longer-lived or deployed analytics storage can be added later.

## Verify the load

```bash
python - <<'PY'
import duckdb
with duckdb.connect('data/football.duckdb', read_only=True) as con:
    for table in ('raw.matches', 'raw.teams', 'raw.standings', 'metadata.pipeline_runs'):
        print(table, con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
    print(con.execute('SELECT run_id, status, rows_received, rows_inserted, rows_updated FROM metadata.pipeline_runs ORDER BY started_at DESC LIMIT 5').fetchall())
PY
pytest -q
```

## Data-quality strategy and limits

Python tests use mocked API responses and need no token. dbt checks keys, references, one-row-per-match grain, two team rows per completed match, accepted team results, analytical mart grains and metric reconciliation. Empty API windows are recorded without deleting historical rows. See [data dictionary](docs/data_dictionary.md) for the full rules.

The API token is required for a real ingestion. The database file and `.env` are excluded by `.gitignore`. The current team dimension keeps the latest team attributes rather than historical versions. The scheduled workflow publishes a short-lived DuckDB artifact; it does not deploy the dashboard.

## Future improvements

- Persist scheduled runs in object storage so incremental extraction can continue across GitHub jobs.
- Add season-grained team membership and historical attributes.
- Reconcile calculated rankings with official standings and competition-specific tie-breakers.
- Publish a hosted dashboard and verified screenshots.
- Add more competitions and historical season backfills after checking API plan limits.

The [portfolio case study](docs/portfolio_case_study.md) summarizes the engineering choices and a dated validation snapshot. This repository has not been connected to a GitHub remote in the current workspace, so the workflow definitions still need a first hosted run.

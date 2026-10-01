# Portfolio case study: football analytics platform

## Problem

Football API data is nested, changes after publication, and is difficult to analyze directly. Match status and score updates make one-off CSV exports stale. A useful analytical dataset needs repeatable extraction, stable keys, documented measures and visible data-quality checks.

## Solution

This project uses Python for authenticated extraction and operational control, DuckDB for the local raw warehouse, dbt SQL for transformation, and Streamlit with Plotly for exploration. The dashboard reads materialized marts rather than recalculating standings in Python. GitHub Actions demonstrates CI without a live token and a scheduled pipeline that publishes a DuckDB artifact.

## Engineering decisions

- Raw tables retain source JSON and use API IDs for idempotent upserts.
- A run record captures start/end times, status, received rows and inserted/updated counts.
- A full season is loaded once locally; subsequent runs refresh a configurable date window so fixtures and recent results can change.
- `fact_matches` has one row per match. Completed-match metrics remain null for unplayed fixtures.
- `int_team_matches` creates two team-perspective rows for each completed match, simplifying downstream metrics.
- dbt tests protect keys, references, expected grains and aggregate reconciliation.
- The scheduled workflow uploads a DuckDB artifact because GitHub-hosted runners do not retain the local database between runs.

## Demonstration path

1. Run `make pipeline` with a valid API token.
2. Query `metadata.pipeline_runs` and the four raw tables to show ingestion and idempotency.
3. Run `make dbt-build` and inspect `fact_matches`, `mart_league_table` and `stg_standings`.
4. Open `make dashboard`, filter a team, inspect recent form and compare a pair head to head.
5. Show `.github/workflows/ci.yml` and its token-free fixture, then explain the artifact strategy in `pipeline.yml`.

## Verified local snapshot

On **2026-10-01**, the PL 2026 warehouse contained 380 matches (50 finished, 330 timed), 20 teams, 60 official standing rows and a 380-row match fact. A live rolling-window request updated 10 existing matches without inserting duplicates. The dbt build passed 90 of 90 steps on the live warehouse and on the CI fixture. These counts are a dated snapshot, not a promise about later seasons or runs.

## Limits and next steps

The calculated league table uses common points/goal tie-breakers and may differ from official standings. Team attributes are latest-loaded rather than historically versioned. Scheduled GitHub jobs perform a fresh full load because artifacts are published for demonstration, not restored as a persistent store. Future iterations could add season-grained team membership, persistent object storage, official-vs-calculated reconciliation and a hosted dashboard.

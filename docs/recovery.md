# Warehouse recovery

How the DuckDB warehouse survives failures, and how to recover manually.

## Design

- **One transaction per competition** (`ingest()`): any error rolls back that
  competition only; previously committed competitions are untouched.
- **Validate-then-publish**: `fd-refresh.yml` runs `validate_warehouse.py`
  (page reads, full scans, row minimums, recent DQ failures) *before*
  uploading. A failed gate skips the upload step, so the previous artifact
  version stays the latest valid copy. Corrupted or unvalidated databases are
  never published.
- **Retention**: each upload creates a new immutable artifact version;
  `retention-days: 14` keeps two weeks of known-good copies. Older versions
  age out automatically — see limits below.
- **Quota/rate aborts** record `SKIPPED`/`FAILED` rows and exit without
  touching raw tables (rollback); the next window resumes normally.

## Manual recovery

```bash
# List available warehouse versions (newest first)
gh run list --repo madhielyousfi/football-analytics-platform --workflow fd-refresh.yml --limit 5

# Download the last known-good artifact (replace RUN_ID)
gh run download RUN_ID --repo madhielyousfi/football-analytics-platform \
  --name football-season-db --dir /tmp/recovery

# Validate before trusting it
.venv/bin/python -m scripts.validate_warehouse --db /tmp/recovery/football.duckdb

# Promote locally (never overwrite without a backup)
cp data/football.duckdb /tmp/football-backup-$(date +%F).duckdb
cp /tmp/recovery/football.duckdb data/football.duckdb
```

## Limitations (GitHub Actions artifacts)

- Artifacts are **immutable per run** and expire after `retention-days`
  (currently 14). There is no built-in "latest stable pointer" beyond the
  newest successful run's artifact.
- Artifact storage quota is shared per repository; very large or frequent
  uploads can exhaust it. Current DB (~23 MB every 6 h × 14 d) is well inside
  limits, but monitor usage if the warehouse grows 10×.
- The scheduled `demo-refresh.yml` commits `data/demo.duckdb` to git, which
  doubles as a coarse second copy — not a backup strategy.

## Free-compatible longer retention (recommended if data grows)

- Raise `retention-days` toward the plan maximum, **or**
- Mirror each validated artifact to Cloudflare R2 (10 GB free) with
  `rclone` in the workflow, **or**
- Commit weekly snapshots to a separate `warehouse-snapshots` branch
  (keeps main history clean while preserving restore points).

## What is NOT covered

- Simultaneous corruption of the working copy *and* all retained artifacts
  (mitigate with one of the options above).
- The ephemeral Streamlit Cloud database (documented in README; out of scope).

# New web stack (2026 remake)

The Streamlit dashboard (`dashboard/`) still works and is kept for local
data-checks. The production frontend is now **Next.js + FastAPI**:

```text
DuckDB marts ──read-only──▶ FastAPI (api/main.py, :8000) ──REST/JSON──▶ Next.js 14 (frontend/, :3000)
```

## Why this stack (research summary, Oct 2026)
- **Next.js 14 App Router + React 18 + TypeScript strict** — file-based routing,
  static prerender for all 6 pages, shared layout/sidebar, per-page 98–219 kB
  first-load JS (verified with `npm run build`).
- **Tailwind CSS 3 + shadcn-style owned primitives** (`app/globals.css`: `.card`,
  `.badge`, `.input`, table classes) — no component-library lock-in; the 2026
  consensus (shadcn/ui on Radix) is mirrored as copy-owned code for portability.
- **TanStack React Query v5** — server-state caching (`staleTime` 60s), one query
  per data need, skeleton loading states, no refetch-on-focus storms.
- **Recharts 2** — composable Area/Donut/Bar/Line charts with a shared dark theme
  (`components/charts.tsx`); fixed heights prevent layout shift.
- **lucide-react + clsx** — icons and conditional nav states.
- **FastAPI + DuckDB (read-only)** — the validated 2026 Python-analytics pattern:
  Pydantic-validated, OpenAPI-documented endpoints; parameterized SQL mirroring
  `dashboard/queries.py`; CORS locked to the web origin; safe to share with
  mobile/CLI later (unlike Next.js API routes). No auth — local-first, single user.

## Run it
```bash
make api        # FastAPI on :8000 (needs data/football.duckdb + dbt build)
make web        # Next.js dev on :3000 (needs NEXT_PUBLIC_API_URL, see frontend/.env.example)
make web-build  # production build check
```
Or manually: `.venv/bin/python -m uvicorn api.main:app --port 8000` and
`npm --prefix frontend run dev`. OpenAPI docs at `http://localhost:8000/docs`.

## Pages → old Streamlit mapping
| Next.js route | Streamlit page | API source |
|---|---|---|
| `/` Overview | `pages/overview.py` | overview, league-table, goal-trends, match-outcomes, all-team-form, home-away |
| `/league` | `pages/league.py` | league-table, all-team-form, home-away |
| `/teams` | `pages/teams.py` | all-team-form, team-performance, home-away, team-progression |
| `/matches` | `pages/matches.py` | matches, match-filter-options, all-team-form |
| `/head-to-head` | `pages/head_to_head.py` | head-to-head, head-to-head-matches |
| `/pipeline` | `pages/pipeline.py` | pipeline-runs |

Selection state (competition/season) is shared via React context +
`localStorage` (`components/selection.tsx`), replacing Streamlit session state.
Mobile gets inline filter selects + bottom tab bar; desktop keeps the sidebar.

## Deploy notes
- **Live demo (GitHub Pages):** `.github/workflows/pages.yml` exports a JSON
  snapshot from `data/demo.duckdb` (`scripts/export_static_data.py`), builds the
  frontend with `NEXT_PUBLIC_DATA_MODE=static` + repo basePath, and publishes
  `frontend/out`. Pushes to `main` touching `frontend/`, the exporter, the demo
  DB, or the workflow redeploy automatically. Refresh the snapshot with
  `cp data/football.duckdb data/demo.duckdb` after a new ingestion + dbt build.
  The static demo shows baked data only: live polling, push alerts and the
  subscribe button degrade to informative empty/demo states.
- **Favorites (no accounts):** followed teams/players/fixtures live in
  `localStorage` (`components/favorites.tsx`); the ★ toggle appears on team,
  player and fixture headers, and `/live` surfaces a "My games" section
  (name-normalized across providers).
- **Goal alerts (Web Push, needs API + poller):** `python scripts/gen_vapid.py`
  creates `VAPID_*` keys; the browser subscribes via `public/sw.js` +
  `POST /api/push/subscribe`; `run_live_poll` diffs scores per cycle and sends
  goal notes (`APP_BASE_URL` links back to `/fixture/{id}`), pruning dead
  endpoints. Requires `API_FOOTBALL_KEY` and VAPID secrets — unavailable on the
  static demo by design.
- Local static preview: `make web-static`, then serve `frontend/out`.
- Full stack → Vercel (frontend, `NEXT_PUBLIC_API_URL`) + Render/Fly
  (`uvicorn api.main:app`, `CORS_ORIGINS` set to the Vercel URL).
- UI/UX contribution rules live in `frontend/SKILLS.md`.

# Frontend UI/UX Skills — Football Intelligence Web

How to build and extend the Next.js frontend so every page stays fast,
responsive, and consistent. Distilled from 2026 production-dashboard research
(Next.js App Router + shadcn-style + TanStack Query + Recharts patterns).

## 1. Stack contract (do not regress)
- Next.js 14 App Router, React 18, TypeScript strict, Tailwind CSS 3.
- Server state: TanStack React Query (`staleTime` 60s, no refetch-on-focus).
- Charts: Recharts only; fixed-height containers (`h-[240-280px]`) to prevent CLS.
- Icons: lucide-react. No emoji in chrome UI (page content may use ⚽ sparingly).
- API: FastAPI owns all SQL. Frontend never touches DuckDB. Typed via `lib/types.ts`.

## 2. Layout & responsiveness
- Desktop: sticky 270px sidebar + max-w-[1200px] content column.
- Mobile (`<lg`): sidebar hidden; competition/season `<select>`s render inline
  (`MobileFilters`); bottom tab bar (`MobileNav`, 6 tabs) with `pb-24` on `<main>`.
- Grids: `grid gap-4 sm:grid-cols-2 xl:grid-cols-4` for KPIs; `xl:grid-cols-3`
  with `xl:col-span-2` for table+chart pairs. Tables always inside
  `overflow-x-auto`. Never let a chart or table cause horizontal page scroll.

## 3. Visual system (`app/globals.css`)
- Dark theme: bg `#070B12`, surface `#0F1622`/`#151D2A`, line `rgba(255,255,255,.08)`.
- Accent green `#22C55E` (primary/live), cyan `#06B6D4`, violet `#8B5CF6`,
  amber `#F59E0B`, red `#EF4444`. Text: white / `#94A3B8` / `#64748B`.
- Primitives: `.card`, `.card-title` (+ right-aligned `<span>` meta),
  `.eyebrow`, `.h-display`, `.badge`, `.input`, `.table-head/.table-cell`,
  `.skeleton`. Reuse — don't invent one-off card styles.
- Position colors: top-4 green, 5–6 cyan, bottom-3 red (see `LeagueTable`).

## 4. Data-fetching rules
- Selection (competition/season) lives in `components/selection.tsx`, persisted
  to `localStorage`, shared via context. New pages must use `useSelection()` —
  never parse the DB or hardcode IDs.
- One `useQuery` per data need, keyed `["resource", competitionId, season, …]`.
- Loading: `SkeletonGrid` / `.skeleton` blocks (never blank space, never spinner
  walls). Error: `<Empty msg>` with the `make api` hint. Empty data: inline
  sentence ("No completed matches yet."), not an error.
- Number formatting via `fmt()` in `lib/api.ts`; dates sliced to `YYYY-MM-DD`.

## 5. Charts (Recharts)
- `ResponsiveContainer` + fixed parent height; `margin={{ left, right, top, bottom }}`
  (NOT l/r/t/b — type error). Grid `rgba(255,255,255,.07)`, ticks `#94A3B8/10px`.
- Custom `Tip` tooltip (dark card). `displayModeBar`-style clutter: hide dots on
  lines (`dot={false}`), `paddingAngle` on donuts, `-30°` angled x-labels on bars.
- New chart? Add it to `components/charts.tsx`, not inline in a page.

## 6. Accessibility & polish
- Every `<select>` has a `<label>`. Images (crests) have `alt` + `loading="lazy"`;
  `Crest` falls back to initials when `crest_url` is null.
- `FormBadge` W/D/L dots keep text contrast (dark text on green/amber, white on red).
- Bottom nav labels short; badges `● Live from marts` communicate freshness.

## 7. Adding a page (checklist)
1. `app/<route>/page.tsx` as `"use client"` using `useSelection` + `useQuery`.
2. `PageHeader` with eyebrow/title/sub; add nav entry in `components/sidebar.tsx`
   (both `NAV` array entries feed desktop + mobile automatically).
3. Reuse `LeagueTable`, `Crest`, `FormBadge`, `Kpi`, charts. Types in `lib/types.ts`,
   fetch via `api<T>("/api/<route>", params)`.
4. `npm run build` must pass; `curl` the route after `npm run start` (expect 200).
5. If new data is needed, add a FastAPI endpoint in `api/main.py` first —
   parameterized SQL only, read-only connection, `LIMIT` on list endpoints.

"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader, Empty, Crest, SkeletonGrid } from "@/components/ui";
import { normTeam, useFavorites } from "@/components/favorites";
import { PushButton } from "@/components/push-button";
import type { LiveFixture } from "@/lib/types";

const LIVE = new Set(["1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE"]);
const FINISHED = new Set(["FT", "AET", "PEN"]);

const isLive = (m: LiveFixture) => !!m.status_short && LIVE.has(m.status_short);
const isFinished = (m: LiveFixture) => !!m.status_short && FINISHED.has(m.status_short);

function kickoff(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso.slice(0, 16).replace("T", " ") : d.toLocaleString([], {
    weekday: "short", hour: "2-digit", minute: "2-digit", day: "numeric", month: "short",
  });
}

function Row({ m }: { m: LiveFixture }) {
  const live = isLive(m);
  return (
    <Link href={`/fixture/${m.fixture_id}`} className="block hover:bg-white/[0.02]">
    <div className="flex items-center gap-2 border-b border-white/5 px-2 py-3 text-xs last:border-0 sm:text-sm">
      <span className="flex min-w-0 flex-1 items-center gap-2 font-medium text-slate-200">
        <Crest name={m.home_team_name} url={m.home_crest_url} size={20} />
        <span className="truncate">{m.home_team_name}</span>
      </span>
      <span className="flex shrink-0 flex-col items-center gap-1">
        {m.goals_home !== null && m.goals_home !== undefined ? (
          <span className={`rounded-lg border px-2.5 py-1 font-extrabold text-white ${live ? "border-red-500/40 bg-red-500/10" : "border-line bg-surface2"}`}>
            {m.goals_home} – {m.goals_away}
          </span>
        ) : (
          <span className="badge border-white/10 bg-white/5 text-muted">{kickoff(m.fixture_date)}</span>
        )}
        <span className="flex items-center gap-1 text-[0.65rem] text-faint">
          {live && <i className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />}
          {live ? `${m.status_short} ${m.elapsed ?? ""}′` : m.status_short === "NS" || m.status_short === "TBD" ? m.league_name : `${m.status_short} · ${String(m.fixture_date).slice(0, 10)}`}
        </span>
      </span>
      <span className="flex min-w-0 flex-1 items-center justify-end gap-2 font-medium text-slate-200">
        <span className="truncate">{m.away_team_name}</span>
        <Crest name={m.away_team_name} url={m.away_crest_url} size={20} />
      </span>
    </div>
    </Link>
  );
}

export default function LivePage() {
  const [league, setLeague] = useState<string>("");
  const [season, setSeason] = useState<string>("");
  const { teams: favTeams, fixtures: favFixtures } = useFavorites();
  const feed = useQuery({
    queryKey: ["live"],
    queryFn: () => api<LiveFixture[]>("/api/live", { limit: 100 }),
    refetchInterval: (query) => {
      const rows = query.state.data as LiveFixture[] | undefined;
      return rows?.some(isLive) ? 60_000 : false;
    },
  });

  // All hooks above any early return: hook count must never change renders.
  const leagues = useMemo(() => {
    const map = new Map<number, string>();
    (feed.data ?? []).forEach((m) => map.set(m.league_id, m.league_name));
    return Array.from(map.entries());
  }, [feed.data]);
  const seasons = useMemo(
    () => Array.from(new Set((feed.data ?? []).map((m) => m.season))).sort((a, b) => b - a),
    [feed.data],
  );
  const favNames = useMemo(() => new Set(favTeams.map((t) => normTeam(t.name))), [favTeams]);
  const favIds = useMemo(() => new Set(favFixtures.map((f) => f.id)), [favFixtures]);

  if (feed.isLoading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Live" title="Live board" /><SkeletonGrid /></div>);
  if (feed.isError) return <Empty msg="API unreachable. Run `make api` first." />;

  const rows = (feed.data ?? []).filter(
    (m) => (!league || m.league_id === Number(league)) && (!season || m.season === Number(season)),
  );
  const mine = rows.filter((m) => favIds.has(m.fixture_id) || favNames.has(normTeam(m.home_team_name)) || favNames.has(normTeam(m.away_team_name)));
  const live = rows.filter(isLive);
  const upcoming = rows.filter((m) => !isLive(m) && !isFinished(m));
  const results = rows.filter(isFinished);

  return (
    <div>
      <PageHeader
        eyebrow="Live"
        title="Live board"
        sub={live.length > 0 ? `${live.length} live now · auto-refresh every 60s` : "No matches live right now · refreshes automatically when play resumes"}
        right={<span className="flex items-center gap-2">
          <PushButton />
          {live.length > 0
            ? <span className="badge border-red-500/30 bg-red-500/10 text-red-300"><i className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" /> LIVE</span>
            : <span className="badge border-white/10 bg-white/5 text-muted">○ Idle</span>}
        </span>}
      />
      <div className="card mb-4 grid gap-3 sm:grid-cols-2 sm:max-w-xl">
        <div>
          <label className="mb-1 block text-xs text-muted">League</label>
          <select className="input" value={league} onChange={(e) => setLeague(e.target.value)}>
            <option value="">All leagues</option>
            {leagues.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Season</label>
          <select className="input" value={season} onChange={(e) => setSeason(e.target.value)}>
            <option value="">All seasons</option>
            {seasons.map((s) => <option key={s} value={s}>{s}/{String(s + 1).slice(2)}</option>)}
          </select>
        </div>
      </div>
      <p className="mb-4 text-xs text-faint">Live board follows the current window (recent + upcoming). Browse full seasons in Matches, League or Tournaments via the sidebar filters.</p>

      {rows.length === 0 ? (
        <Empty msg="No fixtures in the warehouse yet. Run `make af-backfill` to load games (needs API_FOOTBALL_KEY)." />
      ) : (
        <>
          {mine.length > 0 && (
            <div className="card mb-4 !border-amber-400/20">
              <div className="card-title">★ My games <span>{mine.length} followed</span></div>
              <div className="!p-0">{mine.map((m) => <Row key={m.fixture_id} m={m} />)}</div>
            </div>
          )}
          {live.length > 0 && (
            <div className="card mb-4 !border-red-500/20">
              <div className="card-title">Live now <span>{live.length} in play</span></div>
              <div className="!p-0">{live.map((m) => <Row key={m.fixture_id} m={m} />)}</div>
            </div>
          )}
          {upcoming.length > 0 && (
            <div className="card mb-4">
              <div className="card-title">Upcoming <span>kickoff times local</span></div>
              <div className="!p-0">{upcoming.map((m) => <Row key={m.fixture_id} m={m} />)}</div>
            </div>
          )}
          {results.length > 0 && (
            <div className="card">
              <div className="card-title">Recent results <span>finished</span></div>
              <div className="!p-0">{results.map((m) => <Row key={m.fixture_id} m={m} />)}</div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

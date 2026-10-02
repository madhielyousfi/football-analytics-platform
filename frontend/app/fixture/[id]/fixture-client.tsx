"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader, Empty, Crest, SkeletonGrid } from "@/components/ui";
import { FormationPitch, StatBars } from "@/components/fixture-tabs";
import type { FixtureDetail, LineupRow, MatchEvent, TeamStat } from "@/lib/types";

function iconFor(e: MatchEvent): string {
  const t = (e.event_type ?? "").toLowerCase();
  const d = (e.detail ?? "").toLowerCase();
  if (t.includes("goal")) return d.includes("own") ? "⚽🅾️" : "⚽";
  if (t.includes("card")) return d.includes("red") || d.includes("second yellow") ? "🟥" : "🟨";
  if (t.includes("subst")) return "🔄";
  return "•";
}

function minute(e: MatchEvent): string {
  if (e.elapsed === null || e.elapsed === undefined) return "–";
  return `${e.elapsed}${e.extra_minute ? `+${e.extra_minute}` : ""}′`;
}

export default function FixtureClient({ id }: { id: string }) {
  const [tab, setTab] = useState<"timeline" | "lineups" | "stats">("timeline");
  const detail = useQuery({
    queryKey: ["fixture", id],
    queryFn: () => api<FixtureDetail>("/api/fixture-detail", { fixture_id: id }),
  });
  const lineups = useQuery({
    queryKey: ["fixture-lineups", id],
    queryFn: () => api<LineupRow[]>("/api/fixture-lineups", { fixture_id: id }),
    enabled: tab === "lineups",
  });
  const stats = useQuery({
    queryKey: ["fixture-stats", id],
    queryFn: () => api<TeamStat[]>("/api/fixture-stats", { fixture_id: id }),
    enabled: tab === "stats",
  });

  if (detail.isLoading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Match" title="Loading…" /><SkeletonGrid /></div>);
  if (detail.isError) return <Empty msg="API unreachable. Run `make api` first." />;
  const fx = detail.data?.fixture;
  if (!fx) return (
    <div className="flex flex-col gap-4">
      <PageHeader eyebrow="Match" title="Not backfilled yet" sub="This fixture has no API-Football data in the warehouse." />
      <Empty msg="Run `make af-backfill` (needs API_FOOTBALL_KEY) to load it." />
      <Link href="/matches" className="text-xs font-bold text-pitch hover:underline">← Back to matches</Link>
    </div>
  );

  const events = detail.data?.events ?? [];
  const played = fx.goals_home !== null && fx.goals_home !== undefined;

  return (
    <div>
      <PageHeader eyebrow={fx.league_name} title={`${fx.home_team_name} vs ${fx.away_team_name}`}
        sub={`${fx.round ?? ""} · ${String(fx.fixture_date).slice(0, 10)}${fx.status_long ? ` · ${fx.status_long}` : ""}`} />
      <div className="card">
        <div className="flex items-center justify-between gap-4 py-2">
          <div className="flex flex-1 flex-col items-center gap-2 text-center">
            <Crest name={fx.home_team_name} url={fx.home_crest_url} size={52} />
            <b className="text-white">{fx.home_team_name}</b>
            <span className="text-[0.65rem] text-faint">HOME</span>
          </div>
          <div className="text-center">
            {played ? (
              <p className="text-5xl font-extrabold text-white">{fx.goals_home} – {fx.goals_away}</p>
            ) : (
              <p className="badge border-white/10 bg-white/5 text-muted">{fx.status_short}</p>
            )}
            <p className="mt-2 text-xs text-faint">{fx.elapsed != null ? `${fx.elapsed}′` : fx.status_long ?? ""}</p>
          </div>
          <div className="flex flex-1 flex-col items-center gap-2 text-center">
            <Crest name={fx.away_team_name} url={fx.away_crest_url} size={52} />
            <b className="text-white">{fx.away_team_name}</b>
            <span className="text-[0.65rem] text-faint">AWAY</span>
          </div>
        </div>
      </div>

      <div className="mb-4 flex gap-2">
        {(["timeline", "lineups", "stats"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`rounded-xl px-4 py-2 text-xs font-bold capitalize transition ${tab === t ? "bg-pitch/15 text-green-300 border border-pitch/30" : "bg-surface2 text-muted border border-line hover:text-white"}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === "timeline" && (
      <div className="card">
        <div className="card-title">Timeline <span>{events.length} events</span></div>
        {events.length === 0 ? (
          <p className="text-xs text-faint">No events recorded yet — they load with the events backfill after full time.</p>
        ) : (
          <div className="flex flex-col">
            {events.map((e, i) => (
              <div key={i} className="flex items-center gap-3 border-b border-white/5 py-2.5 text-xs last:border-0 sm:text-sm">
                <span className="w-12 shrink-0 rounded-md bg-white/5 px-1.5 py-1 text-center font-bold text-white">{minute(e)}</span>
                <span className="text-base">{iconFor(e)}</span>
                <span className="min-w-0 flex-1">
                  <b className="text-white">{e.player_name ?? e.detail ?? e.event_type}</b>
                  {e.assist_player_name && <span className="text-muted"> · assist {e.assist_player_name}</span>}
                  <span className="block truncate text-faint">{e.team_name} · {e.detail}</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      )}

      {tab === "lineups" && (
        <LineupsTab rows={lineups.data ?? []} loading={lineups.isLoading}
          homeId={fx.home_team_id} awayId={fx.away_team_id} />
      )}

      {tab === "stats" && (
        <div className="card">
          <div className="card-title">Team statistics <span>home vs away</span></div>
          {stats.isLoading ? <div className="skeleton h-40" /> : <StatBars stats={stats.data ?? []} homeId={fx.home_team_id} />}
        </div>
      )}
      <Link href="/live" className="mt-4 inline-block text-xs font-bold text-pitch hover:underline">← Back to live board</Link>
    </div>
  );
}

function LineupsTab({ rows, loading, homeId, awayId }: {
  rows: LineupRow[]; loading: boolean; homeId: number; awayId: number;
}) {
  if (loading) return <div className="card"><div className="skeleton h-64" /></div>;
  const home = rows.filter((r) => r.team_id === homeId);
  const away = rows.filter((r) => r.team_id === awayId);
  if (rows.length === 0) {
    return (
      <div className="card">
        <div className="card-title">Lineups <span>not available</span></div>
        <p className="text-xs text-faint">Lineups publish ~40 min before kickoff and load with the depth backfill (`make af-backfill --max-depth N`).</p>
      </div>
    );
  }
  const TeamBlock = ({ team, color }: { team: LineupRow[]; color: string }) => {
    const xi = team.filter((r) => r.is_starting);
    const bench = team.filter((r) => !r.is_starting);
    return (
      <div>
        <p className="mb-1 text-sm font-extrabold text-white">{team[0]?.team_name}</p>
        <p className="mb-3 text-xs text-muted">{team[0]?.formation ?? "–"} · {team[0]?.coach_name ?? "–"}</p>
        <FormationPitch rows={team} color={color} />
        <p className="mb-1 mt-4 text-xs font-bold uppercase tracking-wider text-faint">Substitutes</p>
        <div className="flex flex-col">
          {bench.map((p) => (
            <div key={p.player_id} className="flex items-center gap-2 border-b border-white/5 py-1.5 text-xs last:border-0">
              <span className="w-6 text-center font-bold text-faint">{p.number ?? "–"}</span>
              <span className="text-slate-200">{p.player_name}</span>
              <span className="ml-auto text-faint">{p.position ?? ""}</span>
            </div>
          ))}
          {bench.length === 0 && <p className="text-xs text-faint">No bench data.</p>}
        </div>
        {xi.length === 0 && <p className="mt-2 text-xs text-faint">Starting XI not published yet.</p>}
      </div>
    );
  };
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="card"><TeamBlock team={home} color="#16a34a" /></div>
      <div className="card"><TeamBlock team={away} color="#0891b2" /></div>
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader, Empty, Crest, SkeletonGrid } from "@/components/ui";
import type { FixtureDetail, MatchEvent } from "@/lib/types";

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
  const detail = useQuery({
    queryKey: ["fixture", id],
    queryFn: () => api<FixtureDetail>("/api/fixture-detail", { fixture_id: id }),
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

      <div className="card mt-4">
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
      <Link href="/live" className="mt-4 inline-block text-xs font-bold text-pitch hover:underline">← Back to live board</Link>
    </div>
  );
}

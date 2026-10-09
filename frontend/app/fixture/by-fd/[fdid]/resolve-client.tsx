"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader, Empty, Crest, FormBadge, SkeletonGrid } from "@/components/ui";
import type { FdMatch, H2H, Match, TeamFormRow } from "@/lib/types";

export default function ResolveClient({ fdId }: { fdId: string }) {
  const router = useRouter();
  const res = useQuery({
    queryKey: ["resolve", fdId],
    queryFn: () => api<{ fixture_id: number | null }>("/api/fixture-resolve", { fd_match_id: fdId }),
  });

  useEffect(() => {
    if (res.data?.fixture_id) router.replace(`/fixture/${res.data.fixture_id}`);
  }, [res.data, router]);

  const fd = useQuery({
    queryKey: ["fd-match", fdId],
    queryFn: () => api<FdMatch>("/api/fd-match", { match_id: fdId }),
    enabled: res.isSuccess && !res.data?.fixture_id,
  });
  const m = fd.data;

  const form = useQuery({
    queryKey: ["form", m?.competition_id, m?.season],
    queryFn: () => api<TeamFormRow[]>("/api/all-team-form", { competition_id: m!.competition_id, season: m!.season }),
    enabled: !!m,
  });
  const h2h = useQuery({
    queryKey: ["h2h-fd", m?.competition_id, m?.season, m?.home_team_id, m?.away_team_id],
    queryFn: () => api<H2H>("/api/head-to-head", {
      competition_id: m!.competition_id, season: m!.season,
      team_a_id: m!.home_team_id, team_b_id: m!.away_team_id,
    }),
    enabled: !!m,
  });
  const h2hGames = useQuery({
    queryKey: ["h2hm-fd", m?.competition_id, m?.season, m?.home_team_id, m?.away_team_id],
    queryFn: () => api<Match[]>("/api/head-to-head-matches", {
      competition_id: m!.competition_id, season: m!.season,
      team_a_id: m!.home_team_id, team_b_id: m!.away_team_id,
    }),
    enabled: !!m,
  });

  if (res.isLoading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Match" title="Finding detail…" /><SkeletonGrid /></div>);
  if (res.isError) return <Empty msg="API unreachable. Run `make api` first." />;
  if (fd.isLoading) {
    return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Match" title="Loading…" /><SkeletonGrid /></div>);
  }
  if (fd.isError || !fd.data?.match_id) {
    return (
      <div className="flex flex-col gap-4">
        <PageHeader eyebrow="Match" title="Not found" sub="This match is not in the warehouse." />
        <Empty msg="It may belong to a competition/season that has not been ingested." />
        <Link href="/matches" className="text-xs font-bold text-pitch hover:underline">← Back to matches</Link>
      </div>
    );
  }
  if (!m) {
    return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Match" title="Loading…" /><SkeletonGrid /></div>);
  }
  const formOf = (tid: number) => (form.data ?? []).find((f) => f.team_id === tid);
  const played = m.home_goals !== null && m.home_goals !== undefined;

  return (
    <div>
      <PageHeader eyebrow={m.competition_name ?? "Match"} title={`${m.home_team} vs ${m.away_team}`}
        sub={`Matchday ${m.matchday ?? "–"} · ${String(m.match_date).slice(0, 10)} · ${m.match_status}`} />
      <div className="card">
        <div className="flex items-center justify-between gap-4 py-2">
          <div className="flex min-w-0 flex-1 flex-col items-center gap-2 text-center">
            <Crest name={m.home_team} url={m.home_crest_url} size={52} />
            <b className="text-white">{m.home_team}</b>
            <FormBadge form={formOf(m.home_team_id)?.recent_form} />
          </div>
          <div className="text-center">
            {played ? (
              <p className="text-5xl font-extrabold text-white">{m.home_goals} – {m.away_goals}</p>
            ) : (
              <p className="badge border-white/10 bg-white/5 text-muted">{m.match_status}</p>
            )}
            <p className="mt-2 text-xs text-faint">HOME · AWAY</p>
          </div>
          <div className="flex min-w-0 flex-1 flex-col items-center gap-2 text-center">
            <Crest name={m.away_team} url={m.away_crest_url} size={52} />
            <b className="text-white">{m.away_team}</b>
            <FormBadge form={formOf(m.away_team_id)?.recent_form} />
          </div>
        </div>
      </div>

      <div className="card mt-4">
        <div className="card-title">Head-to-head <span>this season</span></div>
        {!h2h.data || h2h.data.matches_played === 0 ? (
          <p className="text-xs text-faint">No meetings this season — first clash or cup tie.</p>
        ) : (
          <>
            <p className="text-center text-2xl font-extrabold text-white">
              {h2h.data.selected_a_wins} – {h2h.data.selected_b_wins}
            </p>
            <p className="mt-1 text-center text-xs text-faint">
              {h2h.data.matches_played} meetings · {h2h.data.draws} draws · goals {h2h.data.selected_a_goals}:{h2h.data.selected_b_goals}
            </p>
            <div className="mt-2 flex flex-col">
              {(h2hGames.data ?? []).slice(0, 5).map((g, i) => (
                <div key={i} className="flex items-center justify-between gap-2 border-b border-white/5 py-2 text-xs last:border-0">
                  <span className="text-faint">{String(g.match_date).slice(0, 10)}</span>
                  <span className="text-slate-200">{g.home_team} vs {g.away_team}</span>
                  <span className="rounded-lg border border-line bg-surface2 px-2 py-0.5 font-bold text-white">{g.home_goals}–{g.away_goals}</span>
                </div>
              ))}
            </div>
          </>
        )}
        <p className="mt-3 text-[0.65rem] text-faint">Full event timeline, lineups and stats load after API-Football backfill for this fixture.</p>
      </div>
      <Link href="/matches" className="mt-4 inline-block text-xs font-bold text-pitch hover:underline">← Back to matches</Link>
    </div>
  );
}

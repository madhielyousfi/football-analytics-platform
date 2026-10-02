"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, fmt } from "@/lib/api";
import { useSelection } from "@/components/selection";
import { MobileFilters } from "@/components/sidebar";
import { PageHeader, Empty, Crest, FormBadge, SkeletonGrid } from "@/components/ui";
import { ProgressionChart } from "@/components/charts";
import { Star, useFavorites } from "@/components/favorites";
import type { TeamFormRow, TeamPerf, HomeAway, Progression } from "@/lib/types";

export default function TeamsPage() {
  const { competitionId, season, loading } = useSelection();
  const params = { competition_id: competitionId!, season: season! };
  const enabled = !loading;
  const teamsQ = useQuery({ queryKey: ["form", competitionId, season], queryFn: () => api<TeamFormRow[]>("/api/all-team-form", params), enabled });
  const [teamId, setTeamId] = useState<number | null>(null);
  const { toggleTeam, isTeam } = useFavorites();
  const activeId = useMemo(() => teamId ?? teamsQ.data?.[0]?.team_id ?? null, [teamId, teamsQ.data]);

  const perf = useQuery({ queryKey: ["perf", competitionId, season, activeId], queryFn: () => api<TeamPerf[]>(`/api/team-performance`, { ...params, team_id: activeId }), enabled: enabled && activeId !== null });
  const haQ = useQuery({ queryKey: ["ha1", competitionId, season, activeId], queryFn: () => api<HomeAway[]>(`/api/home-away`, { ...params, team_id: activeId }), enabled: enabled && activeId !== null });
  const prog = useQuery({ queryKey: ["prog", competitionId, season, activeId], queryFn: () => api<Progression[]>(`/api/team-progression`, { ...params, team_id: activeId }), enabled: enabled && activeId !== null });

  if (loading || teamsQ.isLoading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Clubs" title="Teams" /><SkeletonGrid /></div>);
  if (teamsQ.isError) return <Empty msg="API unreachable. Run `make api` first." />;

  const p = perf.data?.[0];
  const h = haQ.data?.[0];
  const active = teamsQ.data?.find((t) => t.team_id === activeId);

  return (
    <div>
      <PageHeader eyebrow="Clubs" title="Team hub" sub="Results, form, home/away splits and points progression" />
      <div className="mb-4"><MobileFilters /></div>
      <label className="mb-1 block text-xs text-muted">Select team</label>
      <select className="input max-w-md" value={activeId ?? ""} onChange={(e) => setTeamId(Number(e.target.value))}>
        {(teamsQ.data ?? []).map((t) => <option key={t.team_id} value={t.team_id}>{t.team_name}</option>)}
      </select>

      {active && (
        <div className="card mt-4 flex flex-wrap items-center gap-4">
          <Crest name={active.team_name} url={active.crest_url} size={46} />
          <div className="flex-1">
            <h2 className="text-xl font-extrabold text-white">{active.team_name}</h2>
            <p className="text-xs text-muted">{fmt(active.points_last_5)} pts from last 5 · {active.recent_matches ?? 5} tracked</p>
          </div>
          <FormBadge form={active.recent_form} />
          {activeId !== null && (
            <Star on={isTeam(activeId)} label="Follow team"
              onToggle={() => toggleTeam({ id: activeId, name: active.team_name })} />
          )}
        </div>
      )}

      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Played", p ? fmt(Number(p.matches_played ?? 0)) : "…", "W/D/L", `${p ? `${p.wins ?? 0}/${p.draws ?? 0}/${p.losses ?? 0}` : ""}`],
          ["Points", p ? fmt(Number(p.points ?? 0)) : "…", `${p ? fmt(Number(p.points_per_game ?? 0), 2) : ""} per game`],
          ["Goals", p ? `${fmt(Number(p.goals_for ?? 0))} : ${fmt(Number(p.goals_against ?? 0))}` : "…", p ? `Win rate ${fmt(Number(p.win_percentage ?? 0) * 100, 0)}%` : ""],
          ["Home / Away", h ? `${fmt(Number(h.home_points ?? 0))} / ${fmt(Number(h.away_points ?? 0))}` : "…", h ? `H ${fmt(Number(h.home_win_rate ?? 0) * 100, 0)}% · A ${fmt(Number(h.away_win_rate ?? 0) * 100, 0)}%` : ""],
        ].map(([label, value, note]) => (
          <div key={label} className="card"><p className="text-xs font-semibold text-muted">{label}</p>
            <p className="mt-2 text-2xl font-extrabold text-white">{value}</p>
            <p className="mt-1 text-xs text-faint">{note}</p></div>
        ))}
      </div>

      <div className="card mt-4">
        <div className="card-title">Points & goals progression <span>cumulative</span></div>
        {prog.data ? <ProgressionChart data={prog.data} /> : <div className="skeleton h-[260px]" />}
      </div>

      <div className="card mt-4">
        <div className="card-title">Recent matches <span>latest first</span></div>
        <div className="flex flex-col">
          {[...(prog.data ?? [])].reverse().slice(0, 8).map((m) => (
            <div key={m.match_id} className="flex items-center justify-between gap-2 border-b border-white/5 py-2.5 text-xs last:border-0">
              <span className="text-faint">{String(m.match_date).slice(0, 10)} · {m.venue_type === "home" ? "vs" : "at"} {m.opponent_name}</span>
              <span className="flex items-center gap-2">
                <span className="rounded-lg border border-line bg-surface2 px-2 py-0.5 font-bold text-white">{m.goals_for}–{m.goals_against}</span>
                <span className="grid h-6 w-6 place-items-center rounded-full text-[0.65rem] font-extrabold"
                  style={{ background: m.result === "W" ? "#22C55E" : m.result === "D" ? "#F59E0B" : "#EF4444", color: m.result === "L" ? "#fff" : "#080B12" }}>{m.result}</span>
              </span>
            </div>
          ))}
          {(!prog.data || prog.data.length === 0) && <p className="text-xs text-faint">No completed matches yet.</p>}
        </div>
      </div>
    </div>
  );
}

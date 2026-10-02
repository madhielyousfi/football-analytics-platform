"use client";

import { useQuery } from "@tanstack/react-query";
import { api, fmt } from "@/lib/api";
import { useSelection } from "@/components/selection";
import { MobileFilters } from "@/components/sidebar";
import { PageHeader, Kpi, SkeletonGrid, Empty, Crest } from "@/components/ui";
import { LeagueTable } from "@/components/league-table";
import { GoalTrendsChart, OutcomesDonut, AttackBars } from "@/components/charts";
import type { Overview, LeagueRow, GoalTrend, Outcomes, TeamFormRow, HomeAway } from "@/lib/types";

export default function OverviewPage() {
  const { competitionId, season, competitionName, loading } = useSelection();
  const params = { competition_id: competitionId!, season: season! };
  const enabled = !loading;

  const ov = useQuery({ queryKey: ["overview", competitionId, season], queryFn: () => api<Overview>("/api/overview", params), enabled });
  const table = useQuery({ queryKey: ["league", competitionId, season], queryFn: () => api<LeagueRow[]>("/api/league-table", params), enabled });
  const trends = useQuery({ queryKey: ["trends", competitionId, season], queryFn: () => api<GoalTrend[]>("/api/goal-trends", params), enabled });
  const outcomes = useQuery({ queryKey: ["outcomes", competitionId, season], queryFn: () => api<Outcomes>("/api/match-outcomes", params), enabled });
  const form = useQuery({ queryKey: ["form", competitionId, season], queryFn: () => api<TeamFormRow[]>("/api/all-team-form", params), enabled });
  const ha = useQuery({ queryKey: ["ha", competitionId, season], queryFn: () => api<HomeAway[]>("/api/home-away", params), enabled });

  if (loading || (ov.isLoading && !ov.data)) {
    return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Season overview" title="Loading…" /><SkeletonGrid /></div>);
  }
  if (ov.isError) return <Empty msg="API unreachable. Start FastAPI on :8000 (make api) and rebuild marts." />;

  const o = ov.data!;
  const rows = table.data ?? [];
  const formMap: Record<number, string | null> = {};
  (form.data ?? []).forEach((f) => { formMap[f.team_id] = f.recent_form ?? null; });
  const attack = [...rows].sort((a, b) => b.goals_for - a.goals_for).map((r) => ({ name: r.team_name, value: r.goals_for }));
  const defense = [...rows].sort((a, b) => a.goals_against - b.goals_against).map((r) => ({ name: r.team_name, value: r.goals_against }));
  const formSorted = [...(form.data ?? [])].sort((a, b) => b.points_last_5 - a.points_last_5).slice(0, 5);

  return (
    <div>
      <PageHeader eyebrow="Season overview" title={`${competitionName}`}
        sub={`Season ${season}/${String((season ?? 0) + 1).slice(2)} · one row per match · tested dbt marts`}
        right={<span className="badge border-pitch/25 bg-pitch/10 text-green-300">● Live from marts</span>} />
      <div className="mb-4"><MobileFilters /></div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Matches played" value={fmt(o.total_matches)} note={`Across ${fmt(o.number_of_teams)} teams`} icon="📅" tint="green" />
        <Kpi label="Total goals" value={fmt(o.total_goals)} note={`${fmt(o.average_goals_per_match, 2)} per match`} icon="⚽" tint="cyan" />
        <Kpi label="Goals / match" value={fmt(o.average_goals_per_match, 2)} note={`Home ${fmt(o.average_home_goals, 2)} · Away ${fmt(o.average_away_goals, 2)}`} icon="📈" tint="violet" />
        <Kpi label="Over 2.5" value={o.matches_over_2_5 != null ? `${fmt(o.matches_over_2_5)}` : "–"} note={`${fmt(o.matches_under_2_5)} under · ${fmt(o.scoreless_draws)} scoreless draws`} icon="🔥" tint="amber" />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <div className="card xl:col-span-2">
          <div className="card-title">League table <span>Top {rows.length} clubs</span></div>
          <LeagueTable rows={rows} formByTeam={formMap} compact />
        </div>
        <div className="card">
          <div className="card-title">Match outcomes <span>W / D / L</span></div>
          {outcomes.data ? <OutcomesDonut data={outcomes.data} /> : <div className="skeleton h-[240px]" />}
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <div className="card xl:col-span-2">
          <div className="card-title">Goals over time <span>per matchday date</span></div>
          {trends.data ? <GoalTrendsChart data={trends.data} /> : <div className="skeleton h-[280px]" />}
        </div>
        <div className="card">
          <div className="card-title">Form guide <span>last 5</span></div>
          <div className="flex flex-col">
            {formSorted.map((f) => (
              <div key={f.team_id} className="flex items-center justify-between gap-2 border-b border-white/5 py-2 text-xs last:border-0">
                <span className="flex items-center gap-2 font-medium text-slate-200"><Crest name={f.team_name} url={f.crest_url} size={20} />{f.team_name}</span>
                <span className="font-extrabold text-white">{f.points_last_5} pts</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="card">
          <div className="card-title">Best attacks <span>goals for</span></div>
          <AttackBars rows={attack} color="#22C55E" />
        </div>
        <div className="card">
          <div className="card-title">Meanest defenses <span>goals against</span></div>
          <AttackBars rows={defense} color="#06B6D4" />
        </div>
      </div>

      {ha.data && ha.data.length > 0 && (
        <p className="mt-4 text-center text-xs text-faint">Home edge: {(ha.data ?? []).filter((d) => Number(d.home_points ?? 0) > Number(d.away_points ?? 0)).length} of {ha.data.length} clubs earn more points at home.</p>
      )}
    </div>
  );
}

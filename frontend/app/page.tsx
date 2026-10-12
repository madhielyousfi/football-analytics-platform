"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api, fmt, timeAgo } from "@/lib/api";
import { useSelection } from "@/components/selection";
import { MobileFilters } from "@/components/sidebar";
import { PageHeader, Kpi, SkeletonGrid, Empty, Crest } from "@/components/ui";
import { LeagueTable } from "@/components/league-table";
import { GoalTrendsChart, OutcomesDonut, AttackBars } from "@/components/charts";
import type { Overview, LeagueRow, GoalTrend, Outcomes, TeamFormRow, HomeAway, Meta, Match } from "@/lib/types";

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
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/api/meta"), staleTime: 5 * 60_000 });
  const upcoming = useQuery({
    queryKey: ["upcoming", competitionId, season],
    queryFn: () => api<Match[]>("/api/upcoming", { ...params, limit: 5 }),
    enabled,
  });

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
        right={<span className="badge border-white/10 bg-white/5 text-muted" title="Scores are delayed on the free plan — not live">
          ↻ Updated {timeAgo(meta.data?.last_success)} · {meta.data?.source ?? "football-data.org"} · delayed
        </span>} />
      <div className="mb-4"><MobileFilters /></div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Matches played" value={fmt(o.total_matches)} note={`Across ${fmt(o.number_of_teams)} teams`} icon="📅" tint="green" />
        <Kpi label="Total goals" value={fmt(o.total_goals)} note={`${fmt(o.average_goals_per_match, 2)} per match`} icon="⚽" tint="cyan" />
        <Kpi label="Goals / match" value={fmt(o.average_goals_per_match, 2)} note={`Home ${fmt(o.average_home_goals, 2)} · Away ${fmt(o.average_away_goals, 2)}`} icon="📈" tint="violet" />
        <Kpi label="Over 2.5" value={o.matches_over_2_5 != null ? `${fmt(o.matches_over_2_5)}` : "–"} note={`${fmt(o.matches_under_2_5)} under · ${fmt(o.scoreless_draws)} scoreless draws`} icon="🔥" tint="amber" />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-5">
        <div className="card md:col-span-3">
          <div className="card-title">Upcoming fixtures <span>scheduled · not live data</span></div>
          {(upcoming.data ?? []).length === 0 && !upcoming.isLoading && (
            <p className="text-xs text-faint">No scheduled fixtures left this season — every match is finished.</p>
          )}
          {upcoming.isLoading && <div className="skeleton h-32" />}
          <div className="flex flex-col">
            {(upcoming.data ?? []).map((m) => (
              <Link key={m.match_id} href={`/fixture/by-fd/${m.match_id}`} className="block hover:bg-white/[0.02]">
                <div className="flex items-center gap-2 border-b border-white/5 px-1 py-2.5 text-xs last:border-0 sm:text-sm">
                  <span className="flex min-w-0 flex-1 items-center gap-2 font-medium text-slate-200">
                    <Crest name={m.home_team} url={m.home_crest_url} size={20} />
                    <span className="truncate">{m.home_team}</span>
                  </span>
                  <span className="flex shrink-0 flex-col items-center gap-1">
                    <span className="badge border-white/10 bg-white/5 text-muted">{m.match_status}</span>
                    <span className="text-[0.65rem] text-faint">{String(m.match_date).slice(0, 10)}</span>
                  </span>
                  <span className="flex min-w-0 flex-1 items-center justify-end gap-2 font-medium text-slate-200">
                    <span className="truncate">{m.away_team}</span>
                    <Crest name={m.away_team} url={m.away_crest_url} size={20} />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
        <div className="card md:col-span-2">
          <div className="card-title">Data status <span>warehouse snapshot</span></div>
          <div className="flex flex-col gap-2 text-xs">
            <div className="flex justify-between gap-2"><span className="text-faint">Source</span><b className="text-white">{meta.data?.source ?? "football-data.org"}</b></div>
            <div className="flex justify-between gap-2"><span className="text-faint">Last refresh</span><b className="text-white">{timeAgo(meta.data?.last_success)}</b></div>
            <div className="flex justify-between gap-2"><span className="text-faint">Matches in marts</span><b className="text-white">{fmt(meta.data?.matches)}</b></div>
            <div className="flex justify-between gap-2"><span className="text-faint">Scores</span><b className="text-amber-300">delayed (free plan)</b></div>
            <div className="flex justify-between gap-2"><span className="text-faint">Finished</span><b className="text-green-300">{fmt(o.total_matches)} played</b></div>
          </div>
          <p className="mt-3 text-[0.65rem] leading-relaxed text-faint">
            Fixtures marked TIMED/SCHEDULED are upcoming · POSTPONED may be rescheduled ·
            nothing here is live: refreshes run every 6 hours.
          </p>
        </div>
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

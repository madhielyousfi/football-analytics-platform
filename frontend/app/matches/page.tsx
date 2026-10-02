"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { useSelection } from "@/components/selection";
import { MobileFilters } from "@/components/sidebar";
import { PageHeader, Empty, Crest, SkeletonGrid } from "@/components/ui";
import type { Match, TeamFormRow } from "@/lib/types";

export default function MatchesPage() {
  const { competitionId, season, loading } = useSelection();
  const params = { competition_id: competitionId!, season: season! };
  const enabled = !loading;
  const teamsQ = useQuery({ queryKey: ["teams", competitionId, season], queryFn: () => api<TeamFormRow[]>("/api/all-team-form", params), enabled });
  const opts = useQuery({
    queryKey: ["match-opts", competitionId, season],
    queryFn: () => api<{ dates: { min_date: string; max_date: string }; matchdays: number[]; statuses: string[] }>("/api/match-filter-options", params),
    enabled,
  });

  const [team, setTeam] = useState<string>("");
  const [day, setDay] = useState<string>("");
  const [status, setStatus] = useState<string>("");

  const list = useQuery({
    queryKey: ["matches", competitionId, season, team, day, status],
    queryFn: () => api<Match[]>("/api/matches", {
      ...params,
      team_id: team || undefined,
      matchday: day || undefined,
      status: status || undefined,
      limit: 300,
    }),
    enabled,
  });

  if (loading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Fixtures" title="Matches" /><SkeletonGrid /></div>);

  return (
    <div>
      <PageHeader eyebrow="Fixtures & results" title="Matches"
        sub={`${list.data?.length ?? 0} matches · filter by team, matchday and status`} />
      <div className="mb-4"><MobileFilters /></div>

      <div className="card mb-4 grid gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs text-muted">Team</label>
          <select className="input" value={team} onChange={(e) => setTeam(e.target.value)}>
            <option value="">All teams</option>
            {(teamsQ.data ?? []).map((t) => <option key={t.team_id} value={t.team_id}>{t.team_name}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Matchday</label>
          <select className="input" value={day} onChange={(e) => setDay(e.target.value)}>
            <option value="">All matchdays</option>
            {(opts.data?.matchdays ?? []).map((m) => <option key={m} value={m}>Matchday {m}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Status</label>
          <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            {(opts.data?.statuses ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {list.isError ? <Empty msg="API unreachable. Run `make api` first." /> : (
        <div className="card !p-3">
          {(list.data ?? []).map((m) => (
            <Link key={m.match_id} href={`/fixture/by-fd/${m.match_id}`} className="block hover:bg-white/[0.02]">
            <div className="flex items-center gap-2 border-b border-white/5 px-2 py-3 text-xs last:border-0 sm:text-sm">
              <span className="flex min-w-0 flex-1 items-center gap-2 font-medium text-slate-200"><Crest name={m.home_team} url={m.home_crest_url} size={20} /><span className="truncate">{m.home_team}</span></span>
              <span className="flex shrink-0 flex-col items-center gap-1">
                {m.home_goals !== null && m.home_goals !== undefined
                  ? <span className="rounded-lg border border-line bg-surface2 px-2.5 py-1 font-extrabold text-white">{m.home_goals} – {m.away_goals}</span>
                  : <span className="badge border-white/10 bg-white/5 text-muted">{m.match_status}</span>}
                <span className="text-[0.65rem] text-faint">MD {m.matchday ?? "–"} · {String(m.match_date).slice(0, 10)}</span>
              </span>
              <span className="flex min-w-0 flex-1 items-center justify-end gap-2 font-medium text-slate-200"><span className="truncate">{m.away_team}</span><Crest name={m.away_team} url={m.away_crest_url} size={20} /></span>
            </div>
            </Link>
          ))}
          {list.isLoading && <div className="skeleton h-40" />}
          {!list.isLoading && (list.data ?? []).length === 0 && <p className="p-4 text-center text-sm text-muted">No matches for these filters.</p>}
        </div>
      )}
    </div>
  );
}

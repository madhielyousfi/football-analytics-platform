"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useSelection } from "@/components/selection";
import { MobileFilters } from "@/components/sidebar";
import { PageHeader, Empty, SkeletonGrid } from "@/components/ui";
import { LeagueTable } from "@/components/league-table";
import { HomeAwayChart } from "@/components/charts";
import type { LeagueRow, TeamFormRow, HomeAway } from "@/lib/types";

export default function LeaguePage() {
  const { competitionId, season, competitionName, loading } = useSelection();
  const params = { competition_id: competitionId!, season: season! };
  const enabled = !loading;
  const table = useQuery({ queryKey: ["league", competitionId, season], queryFn: () => api<LeagueRow[]>("/api/league-table", params), enabled });
  const form = useQuery({ queryKey: ["form", competitionId, season], queryFn: () => api<TeamFormRow[]>("/api/all-team-form", params), enabled });
  const ha = useQuery({ queryKey: ["ha", competitionId, season], queryFn: () => api<HomeAway[]>("/api/home-away", params), enabled });

  if (loading || table.isLoading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Standings" title="League" /><SkeletonGrid /></div>);
  if (table.isError) return <Empty msg="API unreachable. Run `make api` first." />;

  const formMap: Record<number, string | null> = {};
  (form.data ?? []).forEach((f) => { formMap[f.team_id] = f.recent_form ?? null; });

  return (
    <div>
      <PageHeader eyebrow="Standings" title={`${competitionName} table`}
        sub={`Ordered by points → goal difference → goals for · Season ${season}`} />
      <div className="mb-4"><MobileFilters /></div>
      <div className="card">
        <div className="card-title">Full standings <span>{table.data?.length ?? 0} clubs</span></div>
        <LeagueTable rows={table.data ?? []} formByTeam={formMap} />
      </div>
      <div className="card mt-4">
        <div className="card-title">Home vs away points <span>venue split</span></div>
        {ha.data ? <HomeAwayChart data={ha.data} /> : <div className="skeleton h-[280px]" />}
      </div>
      <p className="mt-4 text-xs text-faint">Simplified analytical table — competition-specific head-to-head or disciplinary tie-breaks are not applied. Official standings live in stg_standings.</p>
    </div>
  );
}

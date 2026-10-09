"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Empty, Crest, SkeletonGrid } from "@/components/ui";
import { LeagueTable } from "@/components/league-table";
import type { Competition, GroupRow, KnockoutMatch, LeagueRow } from "@/lib/types";

function prettyStage(stage: string): string {
  return stage.split("_").map((w) => w.charAt(0) + w.slice(1).toLowerCase()).join(" ")
    .replace("Last 16", "Round of 16").replace("Third Place", "3rd Place");
}

function prettyGroup(group: string): string {
  const parts = group.split("_");
  return `Group ${parts[parts.length - 1]}`;
}

function winnerOf(m: KnockoutMatch): "home" | "away" | null {
  if (m.home_goals === null || m.home_goals === undefined) return null;
  if (m.away_goals === null || m.away_goals === undefined) return null;
  if (m.home_goals > m.away_goals) return "home";
  if (m.away_goals > m.home_goals) return "away";
  return null;
}

export default function TournamentsPage() {
  const compsQ = useQuery({
    queryKey: ["competitions"],
    queryFn: () => api<Competition[]>("/api/competitions"),
    staleTime: 5 * 60_000,
  });
  const cups = useMemo(
    () => (compsQ.data ?? []).filter((c) => (c.competition_type ?? "").toUpperCase() === "CUP"),
    [compsQ.data],
  );
  const [cid, setCid] = useState<number | null>(null);
  const [season, setSeason] = useState<number | null>(null);
  const comp = cups.find((c) => c.competition_id === (cid ?? cups[0]?.competition_id)) ?? cups[0] ?? null;
  const activeCid = comp?.competition_id ?? null;
  const activeSeason = season ?? comp?.seasons[0] ?? null;
  const ready = activeCid !== null && activeSeason !== null;

  const groups = useQuery({
    queryKey: ["tournament-groups", activeCid, activeSeason],
    queryFn: () => api<GroupRow[]>("/api/tournament-groups", { competition_id: activeCid, season: activeSeason }),
    enabled: ready,
  });
  const bracket = useQuery({
    queryKey: ["knockout", activeCid, activeSeason],
    queryFn: () => api<KnockoutMatch[]>("/api/knockout", { competition_id: activeCid, season: activeSeason }),
    enabled: ready,
  });
  const leaguePhase = useQuery({
    queryKey: ["league", activeCid, activeSeason],
    queryFn: () => api<LeagueRow[]>("/api/league-table", { competition_id: activeCid, season: activeSeason }),
    enabled: ready,
  });

  const groupNames = useMemo(
    () => Array.from(new Set((groups.data ?? []).map((g) => g.group_name))),
    [groups.data],
  );
  const rounds = useMemo(() => {
    const map = new Map<string, KnockoutMatch[]>();
    (bracket.data ?? []).forEach((m) => {
      if (!map.has(m.stage)) map.set(m.stage, []);
      map.get(m.stage)!.push(m);
    });
    return Array.from(map.entries()).sort(
      (a, b) => (a[1][0]?.round_order ?? 99) - (b[1][0]?.round_order ?? 99),
    );
  }, [bracket.data]);
  const champion = useMemo(() => {
    const fin = (bracket.data ?? []).find((m) => m.stage === "FINAL");
    if (!fin) return null;
    const w = winnerOf(fin);
    if (!w) return null;
    return w === "home" ? fin.home_team_name : fin.away_team_name;
  }, [bracket.data]);

  if (compsQ.isLoading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Tournaments" title="Tournaments" /><SkeletonGrid /></div>);
  if (compsQ.isError) return <Empty msg="API unreachable. Run `make api` first." />;
  if (cups.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <PageHeader eyebrow="Tournaments" title="Tournaments" sub="Group stages and knockout brackets for cups." />
        <Empty msg="No cup competitions ingested yet. Run ingestion with FOOTBALL_COMPETITION=EC FOOTBALL_SEASON=2024, then dbt build." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader eyebrow="Tournaments" title={comp?.competition_name ?? "Tournaments"}
        sub={champion ? `Season ${activeSeason} · 🏆 Champions: ${champion}` : `Season ${activeSeason}`}
        right={champion ? <span className="badge border-amber-400/30 bg-amber-400/10 text-amber-300">🏆 {champion}</span> : undefined} />
      <div className="card mb-4 grid gap-3 sm:grid-cols-2 sm:max-w-xl">
        <div>
          <label className="mb-1 block text-xs text-muted">Tournament</label>
          <select className="input" value={activeCid ?? ""} onChange={(e) => {
            const c = cups.find((x) => x.competition_id === Number(e.target.value));
            if (c) { setCid(c.competition_id); setSeason(c.seasons[0]); }
          }}>
            {cups.map((c) => <option key={c.competition_id} value={c.competition_id}>{c.competition_name}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Season</label>
          <select className="input" value={activeSeason ?? ""} onChange={(e) => setSeason(Number(e.target.value))}>
            {(comp?.seasons ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {groupNames.length > 0 && (
        <>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-faint">Group stage</h2>          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {groupNames.map((g) => (
              <div key={g} className="card">
                <div className="card-title">{prettyGroup(g)} <span>top 2 advance</span></div>
                <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <tbody>
                    {(groups.data ?? []).filter((r) => r.group_name === g).map((r) => (
                      <tr key={r.team_id} className="hover:bg-white/[0.02]">
                        <td className="table-cell text-left">
                          <span className="inline-block min-w-6 border-l-2 pl-1.5 font-bold"
                            style={{ borderColor: r.position <= 2 ? "#22C55E" : "#334155", color: r.position <= 2 ? "#4ADE80" : "#CBD5E1" }}>
                            {r.position}
                          </span>
                        </td>
                        <td className="table-cell text-left font-semibold text-white">{r.team_name}</td>
                        <td className="table-cell">{r.played}</td>
                        <td className="table-cell">{r.goal_difference > 0 ? `+${r.goal_difference}` : r.goal_difference}</td>
                        <td className="table-cell font-extrabold text-white">{r.points}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {groupNames.length === 0 && (leaguePhase.data ?? []).length > 0 && (
        <div className="card">
          <div className="card-title">League phase <span>single table · top 8 advance</span></div>
          <LeagueTable rows={leaguePhase.data ?? []} />
        </div>
      )}

      {rounds.length > 0 && (
        <>
          <h2 className="mb-3 mt-6 text-sm font-bold uppercase tracking-wider text-faint">Knockout bracket</h2>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {rounds.map(([stage, matches]) => (
              <div key={stage} className="w-[260px] shrink-0">
                <p className="mb-2 text-center text-xs font-bold uppercase tracking-wider text-pitch">{prettyStage(stage)}</p>
                <div className="flex flex-col gap-2">
                  {matches.map((m) => {
                    const w = winnerOf(m);
                    return (
                      <div key={m.match_id} className="card !p-3 text-xs">
                        <div className={`flex items-center gap-2 py-1 ${w === "home" ? "font-extrabold text-white" : "text-slate-300"}`}>
                          <Crest name={m.home_team_name ?? "?"} url={m.home_crest_url} size={18} />
                          <span className="min-w-0 flex-1 truncate">{m.home_team_name}</span>
                          <b>{m.home_goals ?? "–"}</b>
                        </div>
                        <div className={`flex items-center gap-2 py-1 ${w === "away" ? "font-extrabold text-white" : "text-slate-300"}`}>
                          <Crest name={m.away_team_name ?? "?"} url={m.away_crest_url} size={18} />
                          <span className="min-w-0 flex-1 truncate">{m.away_team_name}</span>
                          <b>{m.away_goals ?? "–"}</b>
                        </div>
                        <p className="mt-1 text-[0.65rem] text-faint">{m.match_date ? String(m.match_date).slice(0, 10) : m.match_status}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {groups.isSuccess && bracket.isSuccess && groupNames.length === 0 && rounds.length === 0 && (
        <Empty msg="No group or knockout data for this tournament yet." />
      )}
    </div>
  );
}

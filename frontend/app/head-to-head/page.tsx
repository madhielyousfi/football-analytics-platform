"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { predict, pct } from "@/lib/predict";
import { useSelection } from "@/components/selection";
import { MobileFilters } from "@/components/sidebar";
import { PageHeader, Empty, Crest, SkeletonGrid } from "@/components/ui";
import type { H2H, Match, Overview, TeamFormRow, TeamStrength } from "@/lib/types";

export default function H2HPage() {
  const { competitionId, season, loading } = useSelection();
  const params = { competition_id: competitionId!, season: season! };
  const enabled = !loading;
  const teamsQ = useQuery({ queryKey: ["teams", competitionId, season], queryFn: () => api<TeamFormRow[]>("/api/all-team-form", params), enabled });
  const teams = teamsQ.data ?? [];
  const [a, setA] = useState<number | null>(null);
  const [b, setB] = useState<number | null>(null);
  const ta = useMemo(() => a ?? teams[0]?.team_id ?? null, [a, teams]);
  const tb = useMemo(() => b ?? teams[1]?.team_id ?? null, [b, teams]);
  const ready = enabled && ta !== null && tb !== null && ta !== tb;

  const h2h = useQuery({ queryKey: ["h2h", competitionId, season, ta, tb], queryFn: () => api<H2H>("/api/head-to-head", { ...params, team_a_id: ta, team_b_id: tb }), enabled: ready });
  const games = useQuery({ queryKey: ["h2hm", competitionId, season, ta, tb], queryFn: () => api<Match[]>("/api/head-to-head-matches", { ...params, team_a_id: ta, team_b_id: tb }), enabled: ready });
  const strengths = useQuery({
    queryKey: ["strengths", competitionId, season],
    queryFn: () => api<TeamStrength[]>("/api/team-strengths", params),
    enabled,
  });
  const overview = useQuery({
    queryKey: ["overview", competitionId, season],
    queryFn: () => api<Overview>("/api/overview", params),
    enabled,
  });

  const nameA = teams.find((t) => t.team_id === ta)?.team_name ?? "Team A";
  const nameB = teams.find((t) => t.team_id === tb)?.team_name ?? "Team B";
  const crestA = teams.find((t) => t.team_id === ta)?.crest_url;
  const crestB = teams.find((t) => t.team_id === tb)?.crest_url;

  if (loading || teamsQ.isLoading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Rivalry" title="Head-to-Head" /><SkeletonGrid /></div>);
  if (teamsQ.isError) return <Empty msg="API unreachable. Run `make api` first." />;

  const d = h2h.data;
  const strA = (strengths.data ?? []).find((s) => s.team_id === ta);
  const strB = (strengths.data ?? []).find((s) => s.team_id === tb);
  const pred = strA && strB && overview.data ? predict(
    {
      attack_strength: strA.attack_strength, defense_strength: strA.defense_strength,
      home_attack_strength: strA.home_attack_strength ?? strA.attack_strength,
      home_defense_strength: strA.home_defense_strength ?? strA.defense_strength,
      away_attack_strength: strA.away_attack_strength ?? strA.attack_strength,
      away_defense_strength: strA.away_defense_strength ?? strA.defense_strength,
    },
    {
      attack_strength: strB.attack_strength, defense_strength: strB.defense_strength,
      home_attack_strength: strB.home_attack_strength ?? strB.attack_strength,
      home_defense_strength: strB.home_defense_strength ?? strB.defense_strength,
      away_attack_strength: strB.away_attack_strength ?? strB.attack_strength,
      away_defense_strength: strB.away_defense_strength ?? strB.defense_strength,
    },
    overview.data.average_home_goals ?? NaN,
    overview.data.average_away_goals ?? NaN,
  ) : null;

  return (
    <div>
      <PageHeader eyebrow="Rivalry" title="Head-to-Head" sub="Unordered team pair · lower team ID is Team A in the mart" />
      <div className="mb-4"><MobileFilters /></div>
      <div className="card grid gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs text-muted">Team A</label>
          <select className="input" value={ta ?? ""} onChange={(e) => setA(Number(e.target.value))}>
            {teams.map((t) => <option key={t.team_id} value={t.team_id}>{t.team_name}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Team B</label>
          <select className="input" value={tb ?? ""} onChange={(e) => setB(Number(e.target.value))}>
            {teams.map((t) => <option key={t.team_id} value={t.team_id}>{t.team_name}</option>)}
          </select>
        </div>
      </div>

      {ta === tb ? <div className="mt-4"><Empty msg="Pick two different teams to compare." /></div> : (
        <>
          <div className="card mt-4">
            <div className="flex items-center justify-between gap-4 py-2">
              <div className="flex flex-1 flex-col items-center gap-2 text-center"><Crest name={nameA} url={crestA} size={44} /><b className="text-white">{nameA}</b></div>
              <div className="text-center">
                <p className="text-4xl font-extrabold text-white">{d ? `${d.selected_a_wins} – ${d.selected_b_wins}` : "–"}</p>
                <p className="mt-1 text-xs text-faint">{d ? `${d.matches_played} meetings · ${d.draws} draws` : "loading…"}</p>
                <p className="text-xs text-faint">{d ? `Goals ${d.selected_a_goals} : ${d.selected_b_goals}` : ""}</p>
              </div>
              <div className="flex flex-1 flex-col items-center gap-2 text-center"><Crest name={nameB} url={crestB} size={44} /><b className="text-white">{nameB}</b></div>
            </div>
            {d && (
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                {[[`${nameA} wins`, d.selected_a_wins, "#22C55E"], ["Draws", d.draws, "#F59E0B"], [`${nameB} wins`, d.selected_b_wins, "#06B6D4"]].map(([l, v, c]) => (
                  <div key={l as string} className="rounded-xl border border-line bg-surface2 p-3">
                    <p className="text-2xl font-extrabold" style={{ color: c as string }}>{v as number}</p>
                    <p className="mt-1 max-w-full truncate text-[0.65rem] text-faint">{l as string}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card mt-4">
            <div className="card-title">Model prediction <span>Poisson · if {nameA} hosted</span></div>
            {!pred ? (
              <p className="text-xs text-faint">Needs strengths for both teams (dbt mart_team_strengths) — rebuild marts after ingestion.</p>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-2 text-center">
                  {[[`${nameA}`, pred.homeWin, "#22C55E"], ["Draw", pred.draw, "#F59E0B"], [`${nameB}`, pred.awayWin, "#06B6D4"]].map(([l, v, c]) => (
                    <div key={l as string} className="rounded-xl border border-line bg-surface2 p-3">
                      <p className="text-2xl font-extrabold" style={{ color: c as string }}>{pct(v as number)}</p>
                      <p className="mt-1 max-w-full truncate text-[0.65rem] text-faint">{l as string}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
                  <span>Expected goals <b className="text-white">{pred.lambdaHome} – {pred.lambdaAway}</b></span>
                  <span>·</span>
                  <span>Over 2.5 <b className="text-white">{pct(pred.over25)}</b></span>
                  <span>·</span>
                  <span>BTTS <b className="text-white">{pct(pred.btts)}</b></span>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {pred.topScores.map((s) => (
                    <span key={`${s.hg}-${s.ag}`} className="rounded-lg border border-line bg-surface2 px-2 py-1 text-xs font-bold text-white">
                      {s.hg}–{s.ag} <span className="font-medium text-faint">{pct(s.p)}</span>
                    </span>
                  ))}
                </div>
                <p className="mt-3 text-[0.65rem] text-faint">Independent-Poisson baseline from season attack/defense strengths — no xG, no recency weighting, no rho correction.</p>
              </>
            )}
          </div>

          <div className="card mt-4">
            <div className="card-title">Recent meetings <span>up to 10</span></div>
            <div className="flex flex-col">
              {(games.data ?? []).map((m, i) => (
                <div key={i} className="flex items-center justify-between gap-2 border-b border-white/5 py-2.5 text-xs last:border-0 sm:text-sm">
                  <span className="text-faint">{String(m.match_date).slice(0, 10)}</span>
                  <span className="text-slate-200">{m.home_team} vs {m.away_team}</span>
                  <span className="rounded-lg border border-line bg-surface2 px-2 py-0.5 font-bold text-white">{m.home_goals}–{m.away_goals}</span>
                </div>
              ))}
              {(!games.data || games.data.length === 0) && <p className="text-xs text-faint">No completed meetings this season.</p>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

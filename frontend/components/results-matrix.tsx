"use client";

import type { LeagueRow, Match } from "@/lib/types";

function shortName(name: string): string {
  return name.replace(/\sFC$|\sCF$|^AFC\s|^Real\s|^Athletic\s/, "").trim().slice(0, 12);
}

export function ResultsMatrix({ teams, matches }: { teams: LeagueRow[]; matches: Match[] }) {
  const byPair = new Map<string, Match>();
  matches.forEach((m) => {
    byPair.set(`${m.home_team}|${m.away_team}`, m);
  });
  const cell = (home: string, away: string) => {
    if (home === away) return { text: "—", cls: "text-faint" };
    const m = byPair.get(`${home}|${away}`);
    if (!m || m.home_goals === null || m.home_goals === undefined) {
      return { text: "·", cls: "text-faint" };
    }
    const hg = m.home_goals ?? 0;
    const ag = m.away_goals ?? 0;
    const cls = hg > ag ? "bg-pitch/15 text-green-300" : hg === ag ? "bg-amber-400/10 text-amber-300" : "bg-white/5 text-slate-300";
    return { text: `${hg}–${ag}`, cls };
  };
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse">
        <thead>
          <tr>
            <th className="table-head sticky left-0 z-10 bg-surface text-left">H \ A</th>
            {teams.map((t) => (
              <th key={t.team_id} className="table-head min-w-[52px] text-center" title={t.team_name}>
                {shortName(t.team_name)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {teams.map((h) => (
            <tr key={h.team_id}>
              <td className="table-cell sticky left-0 z-10 max-w-[110px] truncate bg-surface text-left font-semibold text-white" title={h.team_name}>
                {shortName(h.team_name)}
              </td>
              {teams.map((a) => {
                const c = cell(h.team_name, a.team_name);
                return (
                  <td key={a.team_id} className="border-b border-white/5 px-1 py-1.5 text-center">
                    <span className={`inline-block min-w-[44px] rounded-md px-1 py-0.5 text-[0.72rem] font-bold ${c.cls}`}>
                      {c.text}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-[0.65rem] text-faint">Rows attack at home · columns defend away · green home win, amber draw.</p>
    </div>
  );
}

"use client";

import Link from "next/link";
import type { LeagueRow } from "@/lib/types";
import { Crest, FormBadge } from "./ui";

export function LeagueTable({ rows, formByTeam, compact }: { rows: LeagueRow[]; formByTeam?: Record<number, string | null>; compact?: boolean }) {
  const show = compact ? rows.slice(0, 8) : rows;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="table-head text-left">#</th>
            <th className="table-head text-left">Team</th>
            <th className="table-head">P</th><th className="table-head">W</th>
            <th className="table-head">D</th><th className="table-head">L</th>
            {!compact && <><th className="table-head">GF</th><th className="table-head">GA</th></>}
            <th className="table-head">GD</th><th className="table-head">Pts</th>
            {!compact && <th className="table-head text-center">Form</th>}
          </tr>
        </thead>
        <tbody>
          {show.map((r) => (
            <tr key={r.team_id} className="hover:bg-white/[0.02]">
              <td className="table-cell text-left">
                <span className="inline-block min-w-6 border-l-2 pl-1.5 font-bold"
                  style={{ borderColor: r.position <= 4 ? "#22C55E" : r.position <= 6 ? "#06B6D4" : r.position > rows.length - 3 ? "#EF4444" : "#334155",
                    color: r.position <= 4 ? "#4ADE80" : r.position <= 6 ? "#22D3EE" : r.position > rows.length - 3 ? "#F87171" : "#CBD5E1" }}>
                  {r.position}
                </span>
              </td>
              <td className="table-cell text-left">
                <span className="flex items-center gap-2 font-semibold text-white"><Crest name={r.team_name} url={r.crest_url} />{r.team_name}</span>
              </td>
              <td className="table-cell">{r.played}</td><td className="table-cell">{r.wins}</td>
              <td className="table-cell">{r.draws}</td><td className="table-cell">{r.losses}</td>
              {!compact && <><td className="table-cell">{r.goals_for}</td><td className="table-cell">{r.goals_against}</td></>}
              <td className="table-cell">{r.goal_difference > 0 ? `+${r.goal_difference}` : r.goal_difference}</td>
              <td className="table-cell font-extrabold text-white">{r.points}</td>
              {!compact && <td className="table-cell text-center"><FormBadge form={formByTeam?.[r.team_id]} /></td>}
            </tr>
          ))}
        </tbody>
      </table>
      {compact && rows.length > 8 && (
        <Link href="/league" className="mt-3 inline-block text-xs font-bold text-pitch hover:underline">View full table →</Link>
      )}
    </div>
  );
}

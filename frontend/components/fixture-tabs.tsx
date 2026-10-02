"use client";

import type { LineupRow, TeamStat } from "@/lib/types";

function parseGrid(grid?: string | null): [number, number] | null {
  if (!grid) return null;
  const m = grid.split(":");
  if (m.length !== 2) return null;
  const line = Number(m[0]);
  const slot = Number(m[1]);
  return Number.isFinite(line) && Number.isFinite(slot) ? [line, slot] : null;
}

export function FormationPitch({ rows, color }: { rows: LineupRow[]; color: string }) {
  const starters = rows.filter((r) => r.is_starting && parseGrid(r.grid));
  const lines = new Map<number, { row: LineupRow; slot: number }[]>();
  starters.forEach((r) => {
    const [line, slot] = parseGrid(r.grid)!;
    if (!lines.has(line)) lines.set(line, []);
    lines.get(line)!.push({ row: r, slot });
  });
  const ordered = Array.from(lines.entries()).sort((a, b) => b[0] - a[0]);
  const n = Math.max(ordered.length, 1);

  return (
    <div className="relative overflow-hidden rounded-xl border border-line" style={{ background: "linear-gradient(180deg,#14532d,#166534 50%,#15803d)" }}>
      <svg viewBox="0 0 100 140" className="absolute inset-0 h-full w-full opacity-30" preserveAspectRatio="none">
        <rect x="2" y="2" width="96" height="136" fill="none" stroke="white" strokeWidth="1" />
        <line x1="2" y1="70" x2="98" y2="70" stroke="white" strokeWidth="1" />
        <circle cx="50" cy="70" r="12" fill="none" stroke="white" strokeWidth="1" />
        <rect x="30" y="2" width="40" height="16" fill="none" stroke="white" strokeWidth="1" />
        <rect x="30" y="122" width="40" height="16" fill="none" stroke="white" strokeWidth="1" />
      </svg>
      <div className="relative grid" style={{ gridTemplateRows: `repeat(${n}, 1fr)`, height: 320 }}>
        {ordered.map(([line, players]) => {
          const sorted = [...players].sort((a, b) => a.slot - b.slot);
          return (
            <div key={line} className="flex items-center justify-around px-4">
              {sorted.map(({ row: p }) => (
                <span key={p.player_id} className="flex flex-col items-center gap-0.5" title={p.player_name ?? ""}>
                  <span className="grid h-7 w-7 place-items-center rounded-full border-2 text-[0.6rem] font-extrabold text-white"
                    style={{ background: color, borderColor: "rgba(255,255,255,.7)" }}>
                    {p.number ?? "–"}
                  </span>
                  <span className="max-w-[64px] truncate rounded bg-black/50 px-1 text-[0.55rem] font-semibold text-white">
                    {(p.player_name ?? "").split(" ").slice(-1)}
                  </span>
                </span>
              ))}
            </div>
          );
        })}
        {ordered.length === 0 && <p className="p-4 text-center text-xs text-white/80">No grid positions available.</p>}
      </div>
    </div>
  );
}

const STAT_ORDER = ["Ball Possession", "Total Shots", "Shots on Goal", "Shots off Goal",
  "Blocked Shots", "Shots insidebox", "Shots outsidebox", "Goalkeeper Saves", "Corner Kicks",
  "Offsides", "Fouls", "Yellow Cards", "Red Cards", "Total passes", "Passes accurate", "Passes %"];

function statNum(value?: string | null): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(String(value).replace("%", ""));
  return Number.isFinite(n) ? n : null;
}

export function StatBars({ stats, homeId }: { stats: TeamStat[]; homeId: number }) {
  const byTeam = new Map<number, Map<string, string | null>>();
  stats.forEach((s) => {
    if (!byTeam.has(s.team_id)) byTeam.set(s.team_id, new Map());
    byTeam.get(s.team_id)!.set(s.stat_type, s.stat_value ?? null);
  });
  const teams = Array.from(byTeam.keys());
  const awayId = teams.find((t) => t !== homeId) ?? teams[1];
  const types = STAT_ORDER.filter((t) => byTeam.get(homeId)?.has(t) || (awayId != null && byTeam.get(awayId)?.has(t)));
  const extra = Array.from(new Set(stats.map((s) => s.stat_type))).filter((t) => !STAT_ORDER.includes(t)).slice(0, 6);
  if (types.length === 0 && extra.length === 0) {
    return <p className="text-xs text-faint">No statistics recorded yet — they load with the depth backfill.</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      {[...types, ...extra].map((t) => {
        const hv = byTeam.get(homeId)?.get(t) ?? null;
        const av = awayId != null ? byTeam.get(awayId)?.get(t) ?? null : null;
        const hn = statNum(hv);
        const an = statNum(av);
        const total = (hn ?? 0) + (an ?? 0);
        const hpct = total > 0 && hn !== null ? (hn / total) * 100 : 50;
        return (
          <div key={t}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <b className="text-white">{hv ?? "–"}</b>
              <span className="text-faint">{t}</span>
              <b className="text-white">{av ?? "–"}</b>
            </div>
            <div className="flex h-1.5 gap-0.5 overflow-hidden rounded-full">
              <span className="rounded-l-full bg-pitch" style={{ width: `${hpct}%` }} />
              <span className="rounded-r-full bg-cyanx" style={{ width: `${100 - hpct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

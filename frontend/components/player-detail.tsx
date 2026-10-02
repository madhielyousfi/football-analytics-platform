"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api, initials } from "@/lib/api";
import { Empty } from "@/components/ui";
import { Star, useFavorites } from "@/components/favorites";
import type { PlayerEntry, PlayerSeason } from "@/lib/types";

export function PlayerAvatar({ name, size = 46 }: { name: string; size?: number }) {
  return (
    <span className="grid flex-none place-items-center rounded-xl bg-gradient-to-br from-violet-500/40 to-cyan-500/30 font-extrabold text-white"
      style={{ width: size, height: size, fontSize: size * 0.36 }}>{initials(name)}</span>
  );
}

export function usePlayerSeason(playerId: number | null) {
  return useQuery({
    queryKey: ["player-season", playerId],
    queryFn: () => api<PlayerSeason>("/api/player-season", { player_id: playerId }),
    enabled: playerId !== null,
  });
}

export function PlayerDetail({ playerId, link = false }: { playerId: number; link?: boolean }) {
  const q = usePlayerSeason(playerId);
  const { togglePlayer, isPlayer } = useFavorites();
  if (q.isLoading) return <div className="card"><div className="skeleton h-48" /></div>;
  if (q.isError) return <Empty msg="API unreachable. Run `make api` first." />;
  const s = q.data?.summary;
  if (!s) return <Empty msg="No backfilled stats for this player yet." />;
  const kpis: [string, string][] = [
    ["Appearances", String(s.appearances)],
    ["Goals", String(s.goals)],
    ["Assists", String(s.assists)],
    ["Avg rating", s.avg_rating != null ? String(s.avg_rating) : "–"],
    ["Minutes", String(s.minutes)],
    ["Shots (on)", `${s.shots_on ?? 0}/${s.shots_total ?? 0}`],
  ];
  return (
    <div className="card">
      <div className="mb-4 flex items-center gap-4">
        <PlayerAvatar name={s.player_name ?? "?"} />
        <div className="flex-1">
          <h3 className="text-lg font-extrabold text-white">
            {link ? <Link href={`/players/${playerId}`} className="hover:underline">{s.player_name}</Link> : s.player_name}
          </h3>
          <p className="text-xs text-muted">{s.team_name}{s.position ? ` · ${s.position}` : ""}</p>
        </div>
        <Star on={isPlayer(playerId)} label="Follow player"
          onToggle={() => togglePlayer({ id: playerId, name: s.player_name ?? `#${playerId}` })} />
      </div>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        {kpis.map(([label, value]) => (
          <div key={label} className="rounded-xl border border-line bg-surface2 p-2.5 text-center">
            <p className="text-lg font-extrabold text-white">{value}</p>
            <p className="mt-0.5 text-[0.62rem] uppercase tracking-wide text-faint">{label}</p>
          </div>
        ))}
      </div>
      <p className="mb-1 mt-4 text-xs font-bold uppercase tracking-wider text-faint">Match log</p>
      <div className="flex flex-col">
        {(q.data?.matches ?? []).slice(0, 12).map((m) => (
          <div key={m.fixture_id} className="flex items-center justify-between gap-2 border-b border-white/5 py-2 text-xs last:border-0">
            <span className="min-w-0 truncate text-slate-200">
              {m.home_team_name} {m.goals_home ?? "–"}–{m.goals_away ?? "–"} {m.away_team_name}
              <span className="block text-faint">{String(m.fixture_date).slice(0, 10)} · {m.minutes ?? 0}′</span>
            </span>
            <span className="flex shrink-0 items-center gap-2">
              {(m.goals ?? 0) > 0 && <span className="font-bold text-green-300">⚽{m.goals}</span>}
              <span className="rounded-md bg-white/5 px-1.5 py-0.5 font-bold text-white">{m.rating ?? "–"}</span>
            </span>
          </div>
        ))}
        {(q.data?.matches ?? []).length === 0 && <p className="text-xs text-faint">No matches logged.</p>}
      </div>
    </div>
  );
}

export function PlayerPicker({ value, onPick, placeholder }: {
  value: number | null; onPick: (p: PlayerEntry | null) => void; placeholder: string;
}) {
  const [text, setText] = useState("");
  const results = useQuery({
    queryKey: ["player-search", text],
    queryFn: () => api<PlayerEntry[]>("/api/player-search", { q: text, limit: 8 }),
    enabled: text.length >= 2,
  });
  return (
    <div className="relative">
      <input className="input" value={text} placeholder={placeholder}
        onChange={(e) => { setText(e.target.value); onPick(null); }} />
      {text.length >= 2 && (results.data ?? []).length > 0 && (
        <div className="absolute inset-x-0 top-full z-30 mt-1 overflow-hidden rounded-xl border border-line bg-surface2 shadow-card">
          {(results.data ?? []).map((p) => (
            <button key={p.player_id} className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs hover:bg-white/5"
              onClick={() => { onPick(p); setText(p.player_name ?? ""); }}>
              <span className="font-semibold text-white">{p.player_name}</span>
              <span className="truncate text-faint">{p.team_name} · {p.appearances} apps</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function CompareBars({ a, b }: { a: PlayerSeason["summary"]; b: PlayerSeason["summary"] }) {
  if (!a || !b) return null;
  const rows: [string, number, number][] = [
    ["Goals", a.goals, b.goals],
    ["Assists", a.assists, b.assists],
    ["Appearances", a.appearances, b.appearances],
    ["Minutes", a.minutes, b.minutes],
    ["Avg rating ×10", Math.round((a.avg_rating ?? 0) * 10), Math.round((b.avg_rating ?? 0) * 10)],
  ];
  return (
    <div className="flex flex-col gap-3">
      {rows.map(([label, va, vb]) => {
        const total = va + vb;
        const apct = total > 0 ? (va / total) * 100 : 50;
        return (
          <div key={label as string}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <b className="text-violet-300">{va}</b>
              <span className="text-faint">{label}</span>
              <b className="text-cyan-300">{vb}</b>
            </div>
            <div className="flex h-1.5 gap-0.5 overflow-hidden rounded-full">
              <span className="rounded-l-full bg-violetx" style={{ width: `${apct}%` }} />
              <span className="rounded-r-full bg-cyanx" style={{ width: `${100 - apct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

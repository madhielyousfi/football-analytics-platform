"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader, Empty, SkeletonGrid } from "@/components/ui";
import { CompareBars, PlayerAvatar, PlayerDetail, PlayerPicker, usePlayerSeason } from "@/components/player-detail";
import type { PlayerEntry, ScorerRow } from "@/lib/types";

export default function PlayersPage() {
  const [selected, setSelected] = useState<PlayerEntry | null>(null);
  const [cmpA, setCmpA] = useState<PlayerEntry | null>(null);
  const [cmpB, setCmpB] = useState<PlayerEntry | null>(null);
  const scorers = useQuery({
    queryKey: ["top-scorers"],
    queryFn: () => api<ScorerRow[]>("/api/top-scorers", { limit: 20 }),
  });
  const seasonA = usePlayerSeason(cmpA?.player_id ?? null);
  const seasonB = usePlayerSeason(cmpB?.player_id ?? null);

  return (
    <div>
      <PageHeader eyebrow="Players" title="Players"
        sub="Search backfilled players, browse scoring leaders, compare two players side-by-side" />
      <div className="card mb-4">
        <div className="card-title">Find a player <span>min 2 letters</span></div>
        <PlayerPicker value={selected?.player_id ?? null} onPick={setSelected} placeholder="Type a player name…" />
      </div>
      {selected && (
        <div className="mb-4"><PlayerDetail playerId={selected.player_id} link /></div>
      )}

      <div className="card mb-4">
        <div className="card-title">Top scorers <span>backfilled fixtures</span></div>
        {scorers.isLoading ? <div className="skeleton h-48" /> : scorers.isError ? (
          <Empty msg="API unreachable. Run `make api` first." />
        ) : (scorers.data ?? []).length === 0 ? (
          <p className="text-xs text-faint">No player stats backfilled yet — run depth backfill (`make af-backfill --max-depth N`).</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead><tr>
                <th className="table-head text-left">#</th><th className="table-head text-left">Player</th>
                <th className="table-head text-left">Team</th><th className="table-head">Apps</th>
                <th className="table-head">Goals</th><th className="table-head">Assists</th><th className="table-head">Rating</th>
              </tr></thead>
              <tbody>
                {(scorers.data ?? []).map((s, i) => (
                  <tr key={s.player_id} className="hover:bg-white/[0.02]">
                    <td className="table-cell text-left font-bold text-white">{i + 1}</td>
                    <td className="table-cell text-left">
                      <Link href={`/players/${s.player_id}`} className="flex items-center gap-2 font-semibold text-white hover:underline">
                        <PlayerAvatar name={s.player_name ?? "?"} size={20} />{s.player_name}
                      </Link>
                    </td>
                    <td className="table-cell text-left">{s.team_name}</td>
                    <td className="table-cell">{s.appearances}</td>
                    <td className="table-cell font-extrabold text-white">{s.goals}</td>
                    <td className="table-cell">{s.assists}</td>
                    <td className="table-cell">{s.avg_rating ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-title">Player comparison <span>season aggregates</span></div>
        <div className="mb-4 grid gap-3 sm:grid-cols-2">
          <PlayerPicker value={cmpA?.player_id ?? null} onPick={setCmpA} placeholder="Player A…" />
          <PlayerPicker value={cmpB?.player_id ?? null} onPick={setCmpB} placeholder="Player B…" />
        </div>
        {seasonA.isLoading || seasonB.isLoading ? <div className="skeleton h-32" /> : (
          seasonA.data?.summary && seasonB.data?.summary ? (
            <div>
              <div className="mb-3 flex items-center justify-between gap-2">
                <span className="flex min-w-0 flex-1 items-center gap-2 text-sm font-bold text-white">
                  <span className="shrink-0"><PlayerAvatar name={seasonA.data.summary.player_name ?? "?"} size={26} /></span>
                  <span className="min-w-0 truncate">{seasonA.data.summary.player_name}</span>
                </span>
                <span className="shrink-0 text-xs font-bold text-faint">VS</span>
                <span className="flex min-w-0 flex-1 items-center justify-end gap-2 text-sm font-bold text-white">
                  <span className="min-w-0 truncate">{seasonB.data.summary.player_name}</span>
                  <span className="shrink-0"><PlayerAvatar name={seasonB.data.summary.player_name ?? "?"} size={26} /></span>
                </span>
              </div>
              <CompareBars a={seasonA.data.summary} b={seasonB.data.summary} />
            </div>
          ) : <p className="text-xs text-faint">Pick two players to compare.</p>
        )}
      </div>
    </div>
  );
}

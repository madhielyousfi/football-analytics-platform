"use client";

import Link from "next/link";
import { PageHeader } from "@/components/ui";
import { PlayerDetail } from "@/components/player-detail";

export default function PlayerPage({ id }: { id: string }) {
  return (
    <div>
      <PageHeader eyebrow="Player" title="Season card" sub="Aggregates + match log from backfilled fixtures" />
      <PlayerDetail playerId={Number(id)} />
      <Link href="/players" className="mt-4 inline-block text-xs font-bold text-pitch hover:underline">← Back to players</Link>
    </div>
  );
}

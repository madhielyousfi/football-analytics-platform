import PlayerPage from "./player-client";
import { snapshotFile } from "@/lib/snapshot";

export function generateStaticParams(): { id: string }[] {
  const players = snapshotFile("af-players.json") as { player_id: number }[] | null;
  const ids = (Array.isArray(players) ? players : []).slice(0, 500).map((p) => ({ id: String(p.player_id) }));
  return ids.length > 0 ? ids : [{ id: "0" }];
}

export default function Page({ params }: { params: { id: string } }) {
  return <PlayerPage id={params.id} />;
}

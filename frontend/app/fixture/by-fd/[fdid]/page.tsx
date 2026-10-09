import ResolveClient from "./resolve-client";
import { snapshotFile } from "@/lib/snapshot";

export function generateStaticParams(): { fdid: string }[] {
  const map = snapshotFile("af-resolve.json") as Record<string, number> | null;
  const ids = new Set<string>(Object.keys(map ?? {}));
  const fd = snapshotFile("fd-matches.json") as { match_id: number }[] | null;
  (Array.isArray(fd) ? fd : []).slice(0, 2000).forEach((r) => ids.add(String(r.match_id)));
  const list = Array.from(ids);
  return (list.length > 0 ? list : ["0"]).map((fdid) => ({ fdid }));
}

export default function ResolvePage({ params }: { params: { fdid: string } }) {
  return <ResolveClient fdId={params.fdid} />;
}

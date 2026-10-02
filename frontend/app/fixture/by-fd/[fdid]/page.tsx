import ResolveClient from "./resolve-client";
import { snapshotFile } from "@/lib/snapshot";

export function generateStaticParams(): { fdid: string }[] {
  const map = snapshotFile("af-resolve.json") as Record<string, number> | null;
  const ids = Object.keys(map ?? {}).map((fdid) => ({ fdid }));
  // Static export requires at least one prerendered path; "0" renders the
  // "no detail yet" state until real backfill data exists.
  return ids.length > 0 ? ids : [{ fdid: "0" }];
}

export default function ResolvePage({ params }: { params: { fdid: string } }) {
  return <ResolveClient fdId={params.fdid} />;
}

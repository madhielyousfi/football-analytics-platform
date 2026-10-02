"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader, Empty, SkeletonGrid } from "@/components/ui";

export default function ResolveClient({ fdId }: { fdId: string }) {
  const router = useRouter();
  const res = useQuery({
    queryKey: ["resolve", fdId],
    queryFn: () => api<{ fixture_id: number | null }>("/api/fixture-resolve", { fd_match_id: fdId }),
  });

  useEffect(() => {
    if (res.data?.fixture_id) router.replace(`/fixture/${res.data.fixture_id}`);
  }, [res.data, router]);

  if (res.isLoading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Match" title="Finding detail…" /><SkeletonGrid /></div>);
  if (res.isError) return <Empty msg="API unreachable. Run `make api` first." />;
  return (
    <div className="flex flex-col gap-4">
      <PageHeader eyebrow="Match" title="No detail yet"
        sub="This match has no API-Football fixture in the warehouse (not backfilled or unmapped team)." />
      <Empty msg="Run `make af-backfill` (needs API_FOOTBALL_KEY) to load it." />
      <Link href="/matches" className="text-xs font-bold text-pitch hover:underline">← Back to matches</Link>
    </div>
  );
}

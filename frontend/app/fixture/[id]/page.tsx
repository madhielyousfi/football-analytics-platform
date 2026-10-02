import FixtureClient from "./fixture-client";
import { snapshotFile } from "@/lib/snapshot";

export function generateStaticParams(): { id: string }[] {
  const fixtures = snapshotFile("af-fixtures.json") as { fixture_id: number }[] | null;
  const ids = (Array.isArray(fixtures) ? fixtures : []).slice(0, 1000).map((f) => ({ id: String(f.fixture_id) }));
  // Static export requires at least one prerendered path; "0" renders the
  // "not backfilled yet" state until real backfill data exists.
  return ids.length > 0 ? ids : [{ id: "0" }];
}

export default function FixturePage({ params }: { params: { id: string } }) {
  return <FixtureClient id={params.id} />;
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Empty } from "@/components/ui";
import type { PipelineRun } from "@/lib/types";

function rel(iso?: string | null): string {
  if (!iso) return "–";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} hr ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

export default function PipelinePage() {
  const runs = useQuery({ queryKey: ["runs"], queryFn: () => api<PipelineRun[]>("/api/pipeline-runs", { limit: 20 }) });

  return (
    <div>
      <PageHeader eyebrow="Operations" title="Pipeline health"
        sub="API → raw → staging → marts · reruns are idempotent on match keys" />
      {runs.isError ? <Empty msg="API unreachable. Run `make api` first." /> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {(runs.data ?? []).slice(0, 4).map((r) => (
              <div key={r.run_id} className="card">
                <p className="text-xs font-semibold text-muted">{r.pipeline_name}</p>
                <p className={`mt-2 inline-flex badge ${r.status === "success" ? "border-pitch/25 bg-pitch/10 text-green-300" : "border-red-500/25 bg-red-500/10 text-red-300"}`}>{r.status}</p>
                <p className="mt-2 text-xs text-faint">+{r.rows_inserted ?? 0} · ~{r.rows_updated ?? 0} · {r.duration_seconds ?? "–"}s · {rel(r.completed_at)}</p>
              </div>
            ))}
          </div>
          <div className="card mt-4">
            <div className="card-title">Recent runs <span>metadata.pipeline_runs</span></div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead><tr>
                  <th className="table-head text-left">Run</th><th className="table-head text-left">Status</th>
                  <th className="table-head">Received</th><th className="table-head">Inserted</th>
                  <th className="table-head">Updated</th><th className="table-head">Duration</th><th className="table-head">Completed</th>
                </tr></thead>
                <tbody>
                  {(runs.data ?? []).map((r) => (
                    <tr key={r.run_id}>
                      <td className="table-cell text-left font-mono text-[0.7rem]">{String(r.run_id).slice(0, 8)}</td>
                      <td className="table-cell text-left"><span className={`badge ${r.status === "success" ? "border-pitch/25 bg-pitch/10 text-green-300" : "border-red-500/25 bg-red-500/10 text-red-300"}`}>{r.status}</span></td>
                      <td className="table-cell">{r.rows_received ?? "–"}</td><td className="table-cell">{r.rows_inserted ?? "–"}</td>
                      <td className="table-cell">{r.rows_updated ?? "–"}</td><td className="table-cell">{r.duration_seconds ?? "–"}s</td>
                      <td className="table-cell">{rel(r.completed_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(!runs.data || runs.data.length === 0) && <p className="p-4 text-center text-sm text-muted">No runs recorded yet.</p>}
            </div>
          </div>
          <div className="card mt-4">
            <div className="card-title">Lineage <span>football-data.org → marts</span></div>
            <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
              {["API v4", "raw.matches", "stg_matches", "int_match_results", "fact_matches", "mart_goal_analysis"].map((s, i, a) => (
                <span key={s} className="flex items-center gap-2">
                  <span className="rounded-[10px] border border-line bg-surface2 px-3 py-2 text-white">{s}</span>
                  {i < a.length - 1 && <span className="text-pitch">→</span>}
                </span>
              ))}
            </div>
            <p className="mt-3 text-xs text-faint">Team branch: int_match_results → int_team_matches → mart_team_performance → mart_league_table. Re-run <code>make pipeline</code> after every ingestion.</p>
          </div>
        </>
      )}
    </div>
  );
}

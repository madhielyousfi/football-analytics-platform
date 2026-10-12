"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, timeAgo } from "@/lib/api";
import { PageHeader, Empty, SkeletonGrid } from "@/components/ui";
import type { Monitoring } from "@/lib/types";

function healthBadge(status: string): string {
  if (status === "HEALTHY") return "border-pitch/25 bg-pitch/10 text-green-300";
  if (status === "WARNING") return "border-amber-400/30 bg-amber-400/10 text-amber-300";
  if (status === "CRITICAL") return "border-red-500/30 bg-red-500/10 text-red-300";
  return "border-white/10 bg-white/5 text-muted";
}

function runBadge(status: string): string {
  if (status === "SUCCESS" || status === "success") return "border-pitch/25 bg-pitch/10 text-green-300";
  if (status === "SKIPPED") return "border-amber-400/30 bg-amber-400/10 text-amber-300";
  if (status === "RUNNING") return "border-cyan-400/30 bg-cyan-400/10 text-cyan-300";
  return "border-red-500/25 bg-red-500/10 text-red-300";
}

export default function MonitoringPage() {
  const q = useQuery({
    queryKey: ["monitoring"],
    queryFn: () => api<Monitoring>("/api/monitoring", { limit: 20 }),
  });

  if (q.isLoading) return (<div className="flex flex-col gap-4"><PageHeader eyebrow="Operations" title="Monitoring" /><SkeletonGrid /></div>);
  if (q.isError) return <Empty msg="API unreachable. Run `make api` first." />;
  const m = q.data!;

  return (
    <div>
      <PageHeader eyebrow="Operations" title="Monitoring"
        sub={m.snapshot ? `Warehouse snapshot as of ${m.generated_at ? String(m.generated_at).slice(0, 16).replace("T", " ") : "export"} — live values in dynamic mode` : "Live pipeline telemetry from persisted run data"}
        right={<span className={`badge ${healthBadge(m.overall)}`}>● {m.overall}</span>} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {m.freshness.map((f) => (
          <div key={`${f.competition}-${f.season}`} className="card min-h-[122px]">
            <div className="flex items-center justify-between text-xs font-semibold text-muted">
              <span>{f.competition} {f.season}</span>
              <span className={`badge ${healthBadge(f.status)}`}>{f.status}</span>
            </div>
            <p className="mt-2 text-[1.4rem] font-extrabold text-white">
              {f.hours_since_success != null ? `${f.hours_since_success}h` : "–"}
            </p>
            <p className="mt-1 text-xs text-faint">
              {f.last_success ? `refreshed ${timeAgo(f.last_success)}` : (f.note ?? "no successful refresh yet")}
              {f.matches_changed === false && f.last_success ? " · no changes" : ""}
              {f.consecutive_failures > 0 ? ` · ${f.consecutive_failures} failed in a row` : ""}
            </p>
          </div>
        ))}
        {m.freshness.length === 0 && (
          <div className="card sm:col-span-2 xl:col-span-4">
            <p className="text-sm text-muted">No competitions tracked yet — run an ingestion to start freshness history.</p>
          </div>
        )}
      </div>

      <div className="card mt-4">
        <div className="card-title">Data quality <span>
          {m.dq?.latest ? `${m.dq.latest.passed}/${m.dq.latest.total} passed · ${timeAgo(m.dq.latest.recorded_at)}` : "no recorded dbt runs yet — recorded after each dbt build"}
        </span></div>
        {(m.dq?.failures ?? []).length === 0 ? (
          <p className="text-xs text-faint">
            {m.dq?.latest ? "All recorded dbt tests passed." : "Run `dbt build` followed by `scripts/record_dbt_results.py` to populate this panel."}
          </p>
        ) : (
          <div className="flex flex-col">
            {(m.dq?.failures ?? []).map((f, i) => (
              <div key={i} className="border-b border-white/5 py-2 text-xs last:border-0">
                <p className="font-bold text-red-300">{f.node_name} · {f.status}</p>
                {f.message && <p className="mt-0.5 text-faint">{String(f.message).slice(0, 300)}</p>}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card mt-4">
        <div className="card-title">Execution history <span>newest first</span></div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead><tr>
              <th className="table-head text-left">Run</th><th className="table-head text-left">Pipeline</th>
              <th className="table-head text-left">Comp</th><th className="table-head text-left">Status</th>
              <th className="table-head">In/Upd</th><th className="table-head">API</th><th className="table-head">Errors</th><th className="table-head">Started</th>
            </tr></thead>
            <tbody>
              {(m.runs ?? []).map((r) => (
                <tr key={r.run_id}>
                  <td className="table-cell text-left font-mono text-[0.7rem]">{String(r.run_id).slice(0, 8)}</td>
                  <td className="table-cell text-left">{r.pipeline_name}</td>
                  <td className="table-cell text-left">{r.competition ?? "–"}</td>
                  <td className="table-cell text-left"><span className={`badge ${runBadge(r.status)}`}>{r.status}</span></td>
                  <td className="table-cell">{r.rows_inserted ?? 0}/{r.rows_updated ?? 0}</td>
                  <td className="table-cell">{r.api_requests ?? "–"}</td>
                  <td className="table-cell text-left">
                    {r.error_category ? <span className="badge border-white/10 bg-white/5 text-muted">{r.error_category}</span> : "–"}
                  </td>
                  <td className="table-cell">{timeAgo(r.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {(m.runs ?? []).length === 0 && <p className="p-4 text-center text-sm text-muted">No runs recorded yet.</p>}
        </div>
      </div>

      <div className="card mt-4">
        <div className="card-title">Incidents <span>{m.incidents.length} active</span></div>
        {m.incidents.length === 0 ? (
          <p className="text-xs text-faint">No active failures. Resolved pipelines disappear from this list automatically.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {m.incidents.map((inc, i) => (
              <div key={i} className="rounded-xl border border-red-500/25 bg-red-500/5 p-3">
                <p className="text-sm font-bold text-white">{inc.pipeline} · {inc.competition ?? "global"} · {inc.category}</p>
                {inc.reason && <p className="mt-1 text-xs text-faint">{String(inc.reason).slice(0, 300)}</p>}
                {inc.remediation && <p className="mt-1 text-xs text-amber-200">Fix: {inc.remediation}</p>}
                {inc.recovery && <p className="mt-1 text-xs text-faint">{inc.recovery}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
      <Link href="/pipeline" className="mt-4 inline-block text-xs font-bold text-pitch hover:underline">← Back to pipeline</Link>
    </div>
  );
}

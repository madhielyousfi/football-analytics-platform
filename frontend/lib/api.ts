const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const STATIC_MODE = process.env.NEXT_PUBLIC_DATA_MODE === "static";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

function csDir(params: Record<string, string | number | null | undefined>): string {
  return `c${params["competition_id"]}_s${params["season"]}`;
}

async function getJson<T>(rel: string): Promise<T> {
  const res = await fetch(`${BASE_PATH}/data/${rel}`);
  if (!res.ok) throw new Error(`Static data missing: ${rel}`);
  return res.json() as Promise<T>;
}

function num(v: unknown): number | null {
  const n = Number(v);
  return v === null || v === undefined || Number.isNaN(n) ? null : n;
}

/** Static-mode resolver: mirrors the FastAPI filtering semantics over snapshot files. */
async function apiStatic<T>(path: string, params: Record<string, string | number | null | undefined>): Promise<T> {
  const cs = params["competition_id"] != null && params["season"] != null ? csDir(params) : "";
  const pick = <R>(rows: R[], key: string, id: string | number | null | undefined): R[] =>
    id === null || id === undefined || id === "" ? rows : rows.filter((r: any) => r[key] === Number(id));

  switch (path) {
    case "/api/competitions": return getJson<T>("competitions.json");
    case "/api/pipeline-runs": {
      const runs = await getJson<any[]>("pipeline-runs.json");
      return runs.slice(0, Number(params["limit"] ?? 20)) as T;
    }
    case "/api/live": {
      let rows: any[] = [];
      try {
        rows = await getJson<any[]>("live.json");
      } catch {
        return [] as T;
      }
      const lid = num(params["league_id"]);
      if (lid !== null) rows = rows.filter((m) => m.league_id === lid);
      return rows.slice(0, Number(params["limit"] ?? 100)) as T;
    }
    case "/api/overview": return getJson<T>(`${cs}/overview.json`);
    case "/api/match-outcomes": return getJson<T>(`${cs}/outcomes.json`);
    case "/api/league-table": return getJson<T>(`${cs}/league-table.json`);
    case "/api/league-comparison": return getJson<T>(`${cs}/league-comparison.json`);
    case "/api/all-team-form": return getJson<T>(`${cs}/all-team-form.json`);
    case "/api/team-performance": {
      const rows = await getJson<any[]>(`${cs}/team-performance.json`);
      return pick(rows, "team_id", params["team_id"]) as T;
    }
    case "/api/home-away": {
      const rows = await getJson<any[]>(`${cs}/home-away.json`);
      return pick(rows, "team_id", params["team_id"]) as T;
    }
    case "/api/goal-trends": return getJson<T>(`${cs}/goal-trends.json`);
    case "/api/team-form": {
      const doc = await getJson<any>(`${cs}/teams/${params["team_id"]}.json`);
      return (doc.form ?? {}) as T;
    }
    case "/api/team-progression": {
      const doc = await getJson<any>(`${cs}/teams/${params["team_id"]}.json`);
      return (doc.progression ?? []) as T;
    }
    case "/api/match-filter-options": return getJson<T>(`${cs}/match-options.json`);
    case "/api/matches": {
      let rows = await getJson<any[]>(`${cs}/matches.json`);
      const tid = num(params["team_id"]);
      if (tid !== null) rows = rows.filter((m) => m.home_team_id === tid || m.away_team_id === tid);
      const md = num(params["matchday"]);
      if (md !== null) rows = rows.filter((m) => m.matchday === md);
      if (params["start_date"]) rows = rows.filter((m) => String(m.match_date) >= String(params["start_date"]));
      if (params["end_date"]) rows = rows.filter((m) => String(m.match_date) <= String(params["end_date"]));
      if (params["status"]) rows = rows.filter((m) => m.match_status === params["status"]);
      return rows.slice(0, Number(params["limit"] ?? 500)) as T;
    }
    case "/api/head-to-head":
    case "/api/head-to-head-matches": {
      const a = Number(params["team_a_id"]);
      const b = Number(params["team_b_id"]);
      const lo = Math.min(a, b);
      const hi = Math.max(a, b);
      try {
        const doc = await getJson<any>(`${cs}/h2h/${lo}_${hi}.json`);
        return (path.endsWith("matches") ? doc.matches : doc.summary) as T;
      } catch {
        return (path.endsWith("matches") ? [] : {
          matches_played: 0, draws: 0, selected_a_wins: 0, selected_b_wins: 0,
          selected_a_goals: 0, selected_b_goals: 0, recent_results: null,
        }) as T;
      }
    }
    default:
      throw new Error(`Unknown static endpoint: ${path}`);
  }
}

export async function api<T>(path: string, params: Record<string, string | number | null | undefined> = {}): Promise<T> {
  if (STATIC_MODE) return apiStatic<T>(path, params);
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== "") qs.set(k, String(v));
  const url = `${BASE}${path}${qs.toString() ? `?${qs}` : ""}`;
  const res = await fetch(url, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export function fmt(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "–";
  return Number(n).toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

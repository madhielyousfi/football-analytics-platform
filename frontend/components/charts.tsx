"use client";

import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line,
} from "recharts";
import type { GoalTrend, Outcomes, HomeAway, Progression } from "@/lib/types";

const GRID = "rgba(255,255,255,0.07)";

function Tip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-line bg-surface2 px-3 py-2 text-xs text-white shadow-card">
      <p className="font-bold">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color || p.payload?.fill }}>{p.name}: {p.value}</p>
      ))}
    </div>
  );
}

export function GoalTrendsChart({ data }: { data: GoalTrend[] }) {
  const rows = data.map((d) => ({ date: d.match_date.slice(0, 10), Goals: d.goals, Avg: d.average_goals }));
  return (
    <div className="h-[280px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={rows} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="date" tick={{ fill: "#94A3B8", fontSize: 10 }} minTickGap={40} tickLine={false} axisLine={{ stroke: GRID }} />
          <YAxis tick={{ fill: "#94A3B8", fontSize: 10 }} tickLine={false} axisLine={false} width={30} />
          <Tooltip content={<Tip />} />
          <Area type="monotone" dataKey="Goals" stroke="#22C55E" fill="#22C55E33" strokeWidth={2.5} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function OutcomesDonut({ data }: { data: Outcomes }) {
  const rows = [
    { name: "Home wins", value: data.home_wins, fill: "#22C55E" },
    { name: "Draws", value: data.draws, fill: "#F59E0B" },
    { name: "Away wins", value: data.away_wins, fill: "#06B6D4" },
  ];
  return (
    <div className="h-[240px]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={rows} dataKey="value" nameKey="name" innerRadius={62} outerRadius={92} paddingAngle={3} strokeWidth={0}>
            {rows.map((r) => <Cell key={r.name} fill={r.fill} />)}
          </Pie>
          <Tooltip content={<Tip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="mt-1 flex flex-wrap justify-center gap-4 text-xs text-muted">
        {rows.map((r) => <span key={r.name} className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full" style={{ background: r.fill }} />{r.name}: <b className="text-white">{r.value}</b></span>)}
      </div>
    </div>
  );
}

export function AttackBars({ rows, dataKey, color }: { rows: { name: string; value: number }[]; dataKey?: string; color: string }) {
  return (
    <div className="flex flex-col gap-2">
      {rows.slice(0, 8).map((r) => {
        const max = Math.max(...rows.map((x) => x.value), 1);
        return (
          <div key={r.name} className="flex items-center gap-2 text-xs">
            <span className="w-[130px] shrink-0 truncate text-slate-200">{r.name}</span>
            <span className="h-2 flex-1 overflow-hidden rounded-full bg-white/5">
              <span className="block h-full rounded-full" style={{ width: `${(r.value / max) * 100}%`, background: color }} />
            </span>
            <b className="w-9 text-right text-white">{r.value}</b>
          </div>
        );
      })}
    </div>
  );
}

export function ProgressionChart({ data }: { data: Progression[] }) {
  const rows = data.map((d) => ({ date: (d.match_datetime ?? d.match_date).slice(0, 10), Points: d.cumulative_points, Goals: d.cumulative_goals }));
  return (
    <div className="h-[260px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="date" tick={{ fill: "#94A3B8", fontSize: 10 }} minTickGap={40} tickLine={false} axisLine={{ stroke: GRID }} />
          <YAxis tick={{ fill: "#94A3B8", fontSize: 10 }} tickLine={false} axisLine={false} width={30} />
          <Tooltip content={<Tip />} />
          <Line type="monotone" dataKey="Points" stroke="#22C55E" strokeWidth={2.5} dot={false} />
          <Line type="monotone" dataKey="Goals" stroke="#8B5CF6" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HomeAwayChart({ data }: { data: HomeAway[] }) {
  const rows = data.slice(0, 10).map((d) => ({ name: String(d.team_name).slice(0, 14), Home: Number(d.home_points ?? 0), Away: Number(d.away_points ?? 0) }));
  return (
    <div className="h-[280px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ left: 0, right: 8, top: 8, bottom: 40 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#94A3B8", fontSize: 9 }} interval={0} angle={-30} textAnchor="end" tickLine={false} axisLine={{ stroke: GRID }} />
          <YAxis tick={{ fill: "#94A3B8", fontSize: 10 }} tickLine={false} axisLine={false} width={28} />
          <Tooltip content={<Tip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
          <Bar dataKey="Home" fill="#22C55E" radius={[5, 5, 0, 0]} />
          <Bar dataKey="Away" fill="#06B6D4" radius={[5, 5, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

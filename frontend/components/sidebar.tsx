"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Home, Shield, Swords, Trophy, Activity, Cable } from "lucide-react";
import clsx from "clsx";
import { useSelection } from "./selection";

const NAV = [
  { href: "/", label: "Overview", icon: Home },
  { href: "/league", label: "League", icon: Trophy },
  { href: "/teams", label: "Teams", icon: Shield },
  { href: "/matches", label: "Matches", icon: CalendarDays },
  { href: "/head-to-head", label: "Head-to-Head", icon: Swords },
  { href: "/pipeline", label: "Pipeline", icon: Activity },
];

export function Sidebar() {
  const path = usePathname();
  const { competitions, competitionId, season, setSelection, competitionName } = useSelection();
  const comp = competitions.find((c) => c.competition_id === competitionId);

  return (
    <aside className="hidden lg:flex w-[270px] shrink-0 flex-col gap-5 border-r border-line bg-[#0D121C] p-5 min-h-screen sticky top-0 h-screen overflow-y-auto">
      <Link href="/" className="flex items-center gap-3 pb-2">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-pitch/15 text-pitch text-xl">⚽</span>
        <span>
          <span className="block font-extrabold tracking-tight text-white leading-none">Football<span className="text-pitch">Intelligence</span></span>
          <span className="mt-1 block text-[0.65rem] font-bold uppercase tracking-[0.15em] text-faint">Analytics Platform</span>
        </span>
      </Link>

      <nav className="flex flex-col gap-1">
        {NAV.map((n) => {
          const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
          return (
            <Link key={n.href} href={n.href}
              className={clsx("flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition",
                active ? "bg-pitch/10 text-white border-l-[3px] border-pitch" : "text-muted hover:bg-white/5 hover:text-white border-l-[3px] border-transparent")}>
              <n.icon size={17} className={active ? "text-pitch" : ""} /> {n.label}
            </Link>
          );
        })}
      </nav>

      <div>
        <p className="mb-2 text-[0.65rem] font-bold uppercase tracking-[0.15em] text-faint">Filters</p>
        <label className="mb-1 block text-xs text-muted">Competition</label>
        <select className="input" value={competitionId ?? ""} onChange={(e) => {
          const c = Number(e.target.value);
          const found = competitions.find((x) => x.competition_id === c);
          if (found) setSelection(c, found.seasons[0]);
        }}>
          {competitions.map((c) => <option key={c.competition_id} value={c.competition_id}>{c.competition_name}</option>)}
        </select>
        <label className="mb-1 mt-3 block text-xs text-muted">Season</label>
        <select className="input" value={season ?? ""} onChange={(e) => competitionId && setSelection(competitionId, Number(e.target.value))}>
          {(comp?.seasons ?? []).map((s) => <option key={s} value={s}>{s}/{String(s + 1).slice(2)}</option>)}
        </select>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-faint"><Cable size={13} /> {competitionName || "…"} · dbt marts · refresh after build</p>
      </div>
    </aside>
  );
}

export function MobileNav() {
  const path = usePathname();
  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 border-t border-line bg-[#0D121C]/95 backdrop-blur px-2 py-2 grid grid-cols-6 gap-1">
      {NAV.map((n) => {
        const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
        return (
          <Link key={n.href} href={n.href} className={clsx("flex flex-col items-center gap-1 rounded-lg py-1.5 text-[0.62rem] font-semibold", active ? "text-pitch" : "text-muted")}>
            <n.icon size={18} /> {n.label.split("-")[0]}
          </Link>
        );
      })}
    </nav>
  );
}

export function MobileFilters() {
  const { competitions, competitionId, season, setSelection } = useSelection();
  const comp = competitions.find((c) => c.competition_id === competitionId);
  return (
    <div className="lg:hidden grid grid-cols-2 gap-2">
      <select className="input" value={competitionId ?? ""} onChange={(e) => {
        const c = Number(e.target.value);
        const found = competitions.find((x) => x.competition_id === c);
        if (found) setSelection(c, found.seasons[0]);
      }}>
        {competitions.map((c) => <option key={c.competition_id} value={c.competition_id}>{c.competition_name}</option>)}
      </select>
      <select className="input" value={season ?? ""} onChange={(e) => competitionId && setSelection(competitionId, Number(e.target.value))}>
        {(comp?.seasons ?? []).map((s) => <option key={s} value={s}>{s}/{String(s + 1).slice(2)}</option>)}
      </select>
    </div>
  );
}

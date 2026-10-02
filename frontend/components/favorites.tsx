"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type FavTeam = { id: number; name: string };
export type FavPlayer = { id: number; name: string };
export type FavFixture = { id: number; label: string };

type Favs = {
  teams: FavTeam[];
  players: FavPlayer[];
  fixtures: FavFixture[];
  toggleTeam: (t: FavTeam) => void;
  togglePlayer: (p: FavPlayer) => void;
  toggleFixture: (f: FavFixture) => void;
  isTeam: (id: number) => boolean;
  isPlayer: (id: number) => boolean;
  isFixture: (id: number) => boolean;
};

const Ctx = createContext<Favs>({
  teams: [], players: [], fixtures: [],
  toggleTeam: () => {}, togglePlayer: () => {}, toggleFixture: () => {},
  isTeam: () => false, isPlayer: () => false, isFixture: () => false,
});

export function useFavorites() { return useContext(Ctx); }

function load<T>(key: string): T[] {
  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function toggleIn<T extends { id: number }>(list: T[], item: T): T[] {
  return list.some((x) => x.id === item.id)
    ? list.filter((x) => x.id !== item.id)
    : [...list, item];
}

export function FavoritesProvider({ children }: { children: React.ReactNode }) {
  const [teams, setTeams] = useState<FavTeam[]>([]);
  const [players, setPlayers] = useState<FavPlayer[]>([]);
  const [fixtures, setFixtures] = useState<FavFixture[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setTeams(load("fi_fav_teams"));
    setPlayers(load("fi_fav_players"));
    setFixtures(load("fi_fav_fixtures"));
    setReady(true);
  }, []);

  useEffect(() => { if (ready) localStorage.setItem("fi_fav_teams", JSON.stringify(teams)); }, [teams, ready]);
  useEffect(() => { if (ready) localStorage.setItem("fi_fav_players", JSON.stringify(players)); }, [players, ready]);
  useEffect(() => { if (ready) localStorage.setItem("fi_fav_fixtures", JSON.stringify(fixtures)); }, [fixtures, ready]);

  const toggleTeam = useCallback((t: FavTeam) => setTeams((p) => toggleIn(p, t)), []);
  const togglePlayer = useCallback((p: FavPlayer) => setPlayers((l) => toggleIn(l, p)), []);
  const toggleFixture = useCallback((f: FavFixture) => setFixtures((l) => toggleIn(l, f)), []);

  const value = useMemo<Favs>(() => ({
    teams, players, fixtures, toggleTeam, togglePlayer, toggleFixture,
    isTeam: (id) => teams.some((t) => t.id === id),
    isPlayer: (id) => players.some((p) => p.id === id),
    isFixture: (id) => fixtures.some((f) => f.id === id),
  }), [teams, players, fixtures, toggleTeam, togglePlayer, toggleFixture]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/** Normalize a club name for cross-provider matching (FD "Arsenal FC" vs AF "Arsenal"). */
export function normTeam(name: string): string {
  const words = name.toLowerCase().replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter(Boolean);
  const suffix = new Set(["fc", "cf", "sc", "ac", "afc"]);
  while (words.length > 1 && suffix.has(words[words.length - 1])) words.pop();
  return words.join(" ");
}

export function Star({ on, onToggle, label }: { on: boolean; onToggle: () => void; label: string }) {
  return (
    <button onClick={onToggle} title={label} aria-label={label} aria-pressed={on}
      className={`grid h-8 w-8 place-items-center rounded-xl border text-base transition ${on ? "border-amber-400/40 bg-amber-400/10" : "border-line bg-surface2 hover:border-white/20"}`}>
      <span className={on ? "text-amber-300" : "text-faint"}>★</span>
    </button>
  );
}

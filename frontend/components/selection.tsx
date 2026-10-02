"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Competition } from "@/lib/types";

type SelCtx = {
  competitions: Competition[];
  competitionId: number | null;
  season: number | null;
  competitionName: string;
  setSelection: (c: number, s: number) => void;
  loading: boolean;
};

const Ctx = createContext<SelCtx>({
  competitions: [], competitionId: null, season: null, competitionName: "",
  setSelection: () => {}, loading: true,
});

export function useSelection() { return useContext(Ctx); }

export function SelectionProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading } = useQuery({
    queryKey: ["competitions"],
    queryFn: () => api<Competition[]>("/api/competitions"),
    staleTime: 5 * 60_000,
  });
  const [cid, setCid] = useState<number | null>(null);
  const [season, setSeason] = useState<number | null>(null);

  useEffect(() => {
    if (!data?.length) return;
    const savedC = Number(localStorage.getItem("fi_comp") ?? NaN);
    const savedS = Number(localStorage.getItem("fi_season") ?? NaN);
    const found = data.find((c) => c.competition_id === savedC);
    if (found && found.seasons.includes(savedS)) {
      setCid(savedC); setSeason(savedS); return;
    }
    setCid((p) => p ?? data[0].competition_id);
    setSeason((p) => p ?? data[0].seasons[0]);
  }, [data]);

  const setSelection = useCallback((c: number, s: number) => {
    setCid(c); setSeason(s);
    localStorage.setItem("fi_comp", String(c));
    localStorage.setItem("fi_season", String(s));
  }, []);

  const value = useMemo<SelCtx>(() => ({
    competitions: data ?? [],
    competitionId: cid,
    season,
    competitionName: data?.find((c) => c.competition_id === cid)?.competition_name ?? "",
    setSelection,
    loading: isLoading || cid === null || season === null,
  }), [data, cid, season, setSelection, isLoading]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

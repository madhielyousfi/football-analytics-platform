"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { SelectionProvider } from "./selection";
import { FavoritesProvider } from "./favorites";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 60_000, retry: 1, refetchOnWindowFocus: false } },
  }));
  return (
    <QueryClientProvider client={client}>
      <SelectionProvider>
        <FavoritesProvider>{children}</FavoritesProvider>
      </SelectionProvider>
    </QueryClientProvider>
  );
}

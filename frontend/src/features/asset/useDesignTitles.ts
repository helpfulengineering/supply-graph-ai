"use client";

/**
 * manifest id -> display title, for surfaces that name a design they do not own.
 *
 * The asset endpoints carry `manifest_id` and nothing else, so without this a
 * fleet list reads as a column of UUIDs. Kept on the catalogue's own low-
 * volatility caching rather than the assets' `staleTime: 0`: design titles do
 * not change while someone triages a unit.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAllOkhList } from "@/api/ohm/okh";
import { formatOkhDisplayTitle } from "@/features/okh/formatOkhDisplayTitle";

export function useDesignTitles(): Map<string, string> {
  const { data } = useQuery({
    queryKey: ["okh-list-all", "asset-design-titles"],
    queryFn: () => fetchAllOkhList(),
  });

  return useMemo(() => {
    const titles = new Map<string, string>();
    for (const item of data?.items ?? []) {
      if (item?.id) titles.set(item.id, formatOkhDisplayTitle(item.title));
    }
    return titles;
  }, [data]);
}

"use client";

/**
 * List state for /assets, held in the URL.
 *
 * Same shape as useOkhList: refinements go through `replace` rather than
 * `push`, so narrowing a filter four times does not cost four presses of Back
 * to leave the page.
 */
import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { listAssets } from "@/api/ohm/asset";
import type { AssetGrouping } from "./assetListModel";
import { parseAssetStatus } from "./assetStatus";

export interface AssetListState {
  status: string;
  manifestId: string;
  query: string;
  grouping: AssetGrouping;
  needsTriageOnly: boolean;
}

const GROUPINGS: readonly AssetGrouping[] = [
  "status",
  "design",
  "location",
  "none",
];

function parseGrouping(raw: string | null): AssetGrouping {
  return GROUPINGS.includes(raw as AssetGrouping)
    ? (raw as AssetGrouping)
    : "status";
}

export function useAssetList() {
  const router = useRouter();
  const pathname = usePathname() ?? "/assets";
  const params = useSearchParams();

  const state: AssetListState = useMemo(
    () => ({
      status: parseAssetStatus(params?.get("status") ?? null) ?? "",
      manifestId: params?.get("design") ?? "",
      query: params?.get("q") ?? "",
      grouping: parseGrouping(params?.get("group") ?? null),
      needsTriageOnly: params?.get("untriaged") === "1",
    }),
    [params],
  );

  const setState = useCallback(
    (patch: Partial<AssetListState>) => {
      const next = { ...state, ...patch };
      const search = new URLSearchParams();
      if (next.status) search.set("status", next.status);
      if (next.manifestId) search.set("design", next.manifestId);
      if (next.query.trim()) search.set("q", next.query.trim());
      if (next.grouping !== "status") search.set("group", next.grouping);
      if (next.needsTriageOnly) search.set("untriaged", "1");
      const qs = search.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, state],
  );

  const query = useQuery({
    queryKey: ["asset-list", state.status, state.manifestId],
    queryFn: () =>
      listAssets({
        status: state.status || undefined,
        manifestId: state.manifestId || undefined,
      }),
    // The global default is a one-hour stale time with localStorage
    // persistence, which is right for a design catalogue and wrong for a work
    // queue: a technician who records triage and comes back would be served
    // the pre-triage list.
    staleTime: 0,
  });

  return { state, setState, query };
}

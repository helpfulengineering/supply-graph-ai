import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { fetchOkhList } from "../../api/ohm/okh";
import type { OkhManifest } from "../../types/okh";
import {
  countSelected,
  deriveFacetGroups,
  FACET_DEFS,
  filterItems,
  type FacetKey,
  type FacetSelections,
} from "./facets";

const PAGE_SIZE = 24;

/**
 * List payloads can include sidecars that parse as manifests with empty title
 * and no licensor; only show rows the GET /okh/:id contract can render.
 */
function isApiRenderableOkhListItem(item: OkhManifest): boolean {
  if (!item.title?.trim()) return false;
  const lic = item.licensor as unknown;
  if (lic == null) return false;
  if (typeof lic === "string") return lic.trim().length > 0;
  if (Array.isArray(lic)) return lic.length > 0;
  if (typeof lic === "object" && "name" in lic) {
    const n = (lic as { name?: unknown }).name;
    return typeof n === "string" && n.trim().length > 0;
  }
  return false;
}

function textMatches(item: OkhManifest, q: string): boolean {
  if (!q) return true;
  const hay = [
    item.title,
    item.function,
    item.description,
    ...(item.keywords ?? []),
    ...(item.manufacturing_processes ?? []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(q.trim().toLowerCase());
}

function parseList(raw: string | null): string[] {
  return raw ? raw.split(",").map((s) => s.trim()).filter(Boolean) : [];
}

export function useOkhCatalog() {
  const [params, setParams] = useSearchParams();

  const query = useQuery({
    queryKey: ["okh-list"],
    queryFn: () => fetchOkhList({ page: 1, page_size: 100 }),
    staleTime: 60_000,
  });

  const filterText = params.get("q") ?? "";
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);

  const selections: FacetSelections = useMemo(() => {
    const s: FacetSelections = {};
    for (const def of FACET_DEFS) s[def.key] = parseList(params.get(def.key));
    return s;
  }, [params]);

  const renderable = useMemo(
    () => (query.data?.items ?? []).filter(isApiRenderableOkhListItem),
    [query.data],
  );

  const facetGroups = useMemo(
    () => deriveFacetGroups(renderable, selections),
    [renderable, selections],
  );

  const matched = useMemo(() => {
    const byFacet = filterItems(renderable, selections);
    return byFacet.filter((i) => textMatches(i, filterText));
  }, [renderable, selections, filterText]);

  const totalItems = matched.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = matched.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function mutate(fn: (p: URLSearchParams) => void) {
    const next = new URLSearchParams(params);
    fn(next);
    next.delete("page"); // any refinement resets to page 1
    setParams(next, { replace: true });
  }

  function toggleFacet(key: FacetKey, value: string) {
    mutate((p) => {
      const cur = parseList(p.get(key));
      const nextVals = cur.includes(value)
        ? cur.filter((v) => v !== value)
        : [...cur, value];
      if (nextVals.length) p.set(key, nextVals.join(","));
      else p.delete(key);
    });
  }

  function clearFacets() {
    mutate((p) => {
      for (const def of FACET_DEFS) p.delete(def.key);
      p.delete("q");
    });
  }

  function setFilterText(text: string) {
    mutate((p) => (text ? p.set("q", text) : p.delete("q")));
  }

  function setPage(next: number) {
    const p = new URLSearchParams(params);
    p.set("page", String(next));
    setParams(p, { replace: true });
  }

  return {
    pageItems,
    totalItems,
    totalPages,
    safePage,
    facetGroups,
    selections,
    selectedCount: countSelected(selections),
    filterText,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    toggleFacet,
    clearFacets,
    setFilterText,
    setPage,
    PAGE_SIZE,
  };
}

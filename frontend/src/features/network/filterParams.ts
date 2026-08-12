import type { NetworkFilters as Filters } from "../../api/ohm/network";
import { mergeParams } from "../../lib/urlState";

/**
 * The network filter set, as a query string.
 *
 * Pure both ways so the network surface can be linked into — the dashboard
 * charts point at `/facilities?country=Germany` — and so the address bar keeps
 * describing what is on screen once the filters are narrowed there.
 */

const FILTER_KEYS = [
  "country",
  "city",
  "process",
  "source",
  "status",
  "region",
  "access_type",
] as const;

export function filtersFromParams(params: URLSearchParams): Filters {
  const filters: Filters = {};
  for (const key of FILTER_KEYS) {
    const value = params.get(key)?.trim();
    if (!value) continue;
    // Source is the one closed set: anything else would filter to nothing.
    if (key === "source") {
      if (value === "local" || value === "mom") filters.source = value;
      continue;
    }
    filters[key] = value;
  }
  return filters;
}

/**
 * The filter set as parameter updates: every key it owns, with the ones it no
 * longer has set to null so a cleared filter is removed rather than left
 * behind.
 *
 * Updates rather than a finished query string, because the filters are no
 * longer the only thing in the address — the look rides there too, and on this
 * page so do the view mode and the page number. A writer that rebuilds from
 * its own state alone drops everyone else's.
 */
export function filterUpdates(filters: Filters): Record<string, string | null> {
  const updates: Record<string, string | null> = {};
  for (const key of FILTER_KEYS) updates[key] = filters[key] ?? null;
  return updates;
}

/**
 * Whether two filter sets would write the same query string.
 *
 * The surface adopts the address whenever it changes underneath it, and
 * `filtersFromParams` returns a fresh object every call — so identity is never
 * equal, and adopting unconditionally would hand React a new object on every
 * navigation, including the ones the surface itself just wrote. That re-keys
 * the filtered query and refetches for no change.
 */
export function sameFilters(a: Filters, b: Filters): boolean {
  return FILTER_KEYS.every((key) => (a[key] ?? null) === (b[key] ?? null));
}

export function filtersToSearch(filters: Filters, base?: URLSearchParams): string {
  return mergeParams(base ?? new URLSearchParams(), filterUpdates(filters));
}

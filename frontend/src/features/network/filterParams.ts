import type { NetworkFilters as Filters } from "../../api/ohm/network";

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

export function filtersToSearch(filters: Filters): string {
  const params = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = filters[key];
    if (value) params.set(key, value);
  }
  return params.toString();
}

import type { NetworkSpace } from "../../api/ohm/network";

/** "laser_cutting" -> "Laser Cutting" (canonical OHM process id → label). */
export function humanizeProcessId(id: string): string {
  return id
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export interface FilterOptions {
  countries: string[];
  regions: string[];
  statuses: string[];
  accessTypes: string[];
  processes: { id: string; label: string }[];
}

function distinct(values: (string | null | undefined)[]): string[] {
  return [...new Set(values.filter((v): v is string => !!v))].sort((a, b) =>
    a.localeCompare(b),
  );
}

/**
 * Derive the filter dropdown options from a set of spaces (pure). Computed from
 * the unfiltered baseline so the options stay comprehensive and stable as the
 * user narrows the (server-filtered) result set.
 */
export function deriveFilterOptions(spaces: NetworkSpace[]): FilterOptions {
  const processIds = distinct(spaces.flatMap((s) => s.processes ?? []));
  return {
    countries: distinct(spaces.map((s) => s.country)),
    regions: distinct(spaces.map((s) => s.region)),
    statuses: distinct(spaces.map((s) => s.status)),
    accessTypes: distinct(spaces.map((s) => s.access_type)),
    processes: processIds.map((id) => ({ id, label: humanizeProcessId(id) })),
  };
}

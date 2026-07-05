import { apiBaseUrl, ApiError, errorMessage } from "./client";

/** A space on the unified network surface (local OKW facility or MoM space). */
export interface NetworkSpace {
  id: string;
  name: string;
  lat: number;
  lon: number;
  source: "local" | "mom";
  city: string | null;
  region: string | null;
  country: string | null;
  status: string | null;
  processes: string[]; // canonical OHM process ids
  access_type: string | null;
  url: string | null;
  /** True when kept despite a local-only filter it can't express (sorted last). */
  ambiguous?: boolean;
}

export interface NetworkData {
  spaces: NetworkSpace[];
  total: number;
  local_count: number;
  mom_count: number;
  dropped_no_coords: number;
  mom_available: boolean;
}

export interface NetworkFilters {
  country?: string;
  city?: string;
  process?: string;
  source?: "local" | "mom";
  status?: string;
  region?: string;
  access_type?: string;
}

const _FILTER_KEYS = [
  "country",
  "city",
  "process",
  "source",
  "status",
  "region",
  "access_type",
] as const;

/**
 * Fetch the unified, server-filtered network surface (local OKW ∪ MoM).
 *
 * Raw fetch (not the generated client) because GET /api/okw/spaces is newer than
 * the committed OpenAPI schema; goes through globalThis.fetch so MSW intercepts.
 * `source=local` skips the MoM fetch entirely; otherwise MoM is included.
 */
export async function fetchNetworkSpaces(
  filters: NetworkFilters = {},
): Promise<NetworkData> {
  const params = new URLSearchParams();
  params.set("include_mom", filters.source === "local" ? "false" : "true");
  for (const key of _FILTER_KEYS) {
    const value = filters[key];
    if (value) params.set(key, value);
  }

  const response = await globalThis.fetch(`${apiBaseUrl}/api/okw/spaces?${params}`);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(body, `Failed to load network spaces (HTTP ${response.status})`),
    );
  }
  const d = (body ?? {}) as Partial<NetworkData>;
  return {
    spaces: (d.spaces ?? []) as NetworkSpace[],
    total: d.total ?? d.spaces?.length ?? 0,
    local_count: d.local_count ?? 0,
    mom_count: d.mom_count ?? 0,
    dropped_no_coords: d.dropped_no_coords ?? 0,
    mom_available: Boolean(d.mom_available),
  };
}

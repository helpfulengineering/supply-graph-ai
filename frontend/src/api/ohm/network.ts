import { apiBaseUrl, ApiError, errorMessage } from "./client";
import type { components } from "../generated/schema";

/**
 * A space on the unified network surface (local OKW facility or MoM space).
 *
 * From the route's response model (#373). `lat`/`lon` are nullable there and
 * were `number` here: local facilities without coordinates are dropped before
 * the response (counted as `dropped_no_coords`), but MoM spaces are not
 * filtered that way, so a null can arrive. `plottable` below is where that is
 * dealt with once, rather than at each map call site.
 */
export type NetworkSpace = components["schemas"]["NetworkSpace"];

/** A space the map can actually place: coordinates present. */
export type PlottableSpace = NetworkSpace & { lat: number; lon: number };

export type NetworkData = Omit<
  components["schemas"]["NetworkSpacesResponse"],
  "success" | "spaces"
> & { spaces: PlottableSpace[] };

/** Spaces with coordinates. A space that cannot be placed is not a map pin. */
export function plottable(spaces: NetworkSpace[]): PlottableSpace[] {
  return spaces.filter(
    (s): s is PlottableSpace => typeof s.lat === "number" && typeof s.lon === "number",
  );
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

  const response = await globalThis.fetch(
    `${apiBaseUrl}/api/okw/spaces?${params}`,
  );
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(
        body,
        `Failed to load network spaces (HTTP ${response.status})`,
      ),
    );
  }
  const d = (body ?? {}) as Partial<
    components["schemas"]["NetworkSpacesResponse"]
  >;
  const spaces = plottable(d.spaces ?? []);
  return {
    spaces,
    total: d.total ?? spaces.length,
    local_count: d.local_count ?? 0,
    mom_count: d.mom_count ?? 0,
    dropped_no_coords: d.dropped_no_coords ?? 0,
    mom_available: Boolean(d.mom_available),
  };
}

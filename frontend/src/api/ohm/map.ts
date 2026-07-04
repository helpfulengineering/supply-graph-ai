import { apiBaseUrl, ApiError, errorMessage } from "./client";

/** A single network-map point (a facility/space with coordinates). */
export interface MapPoint {
  id: string;
  name: string;
  lat: number;
  lon: number;
  source: "local" | "mom";
}

export interface MapData {
  points: MapPoint[];
  local_count: number;
  mom_count: number;
  dropped_no_coords: number;
  /** Whether the Maps of Making layer is available (present, fresh or stale). */
  mom_available: boolean;
}

/**
 * Fetch network-map points: local OKW facilities ∪ Maps of Making spaces.
 *
 * Uses a raw fetch (not the generated client) because GET /api/okw/map is newer
 * than the committed OpenAPI schema; swap to `apiClient` once the schema is
 * regenerated. Goes through globalThis.fetch so MSW still intercepts it.
 */
export async function fetchMapPoints(includeMom = true): Promise<MapData> {
  const url = `${apiBaseUrl}/api/okw/map?include_mom=${includeMom ? "true" : "false"}`;
  const response = await globalThis.fetch(url);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(body, `Failed to load map points (HTTP ${response.status})`),
    );
  }
  const d = (body ?? {}) as Partial<MapData>;
  return {
    points: (d.points ?? []) as MapPoint[],
    local_count: d.local_count ?? 0,
    mom_count: d.mom_count ?? 0,
    dropped_no_coords: d.dropped_no_coords ?? 0,
    mom_available: Boolean(d.mom_available),
  };
}

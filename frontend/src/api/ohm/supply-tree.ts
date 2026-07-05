import { apiClient, ApiError, errorMessage } from "./client";
import type { VisualizationData } from "../../types/supply-tree";

// Solutions are no longer browsed in the UI (per-search, user-specific, stale
// fast) — a supply tree is reached directly from its match. The list endpoint
// (/api/supply-tree/solutions) is left server-side for user-scoped history once
// auth lands.

/** Fetch the visualization bundle for a saved supply-tree solution. */
export async function fetchVisualization(
  solutionId: string,
): Promise<VisualizationData> {
  const { data, error, response } = await apiClient.GET(
    "/api/supply-tree/solution/{solution_id}/visualization",
    { params: { path: { solution_id: solutionId } } },
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load visualization (HTTP ${response.status})`),
    );
  }
  // Bundle is nested under the response envelope's `data`.
  return ((data as { data?: VisualizationData })?.data ?? data) as VisualizationData;
}

import { apiClient, ApiError, errorMessage } from "./client";
import type { VisualizationData } from "../../types/supply-tree";

export interface SolutionSummary {
  id: string;
  okh_id: string | null;
  okh_title: string | null;
  matching_mode: string | null;
  tree_count: number;
  facility_count: number;
  score: number;
  created_at: string | null;
}

/** List saved supply-tree solutions (most recent first). */
export async function listSolutions(): Promise<SolutionSummary[]> {
  const { data, error, response } = await apiClient.GET(
    "/api/supply-tree/solutions",
    { params: { query: { limit: 100 } } },
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load solutions (HTTP ${response.status})`),
    );
  }
  const result = (data as { data?: { result?: unknown[] } })?.data?.result ?? [];
  return result as SolutionSummary[];
}

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

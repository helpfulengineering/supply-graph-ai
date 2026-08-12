import { apiClient, ApiError, errorMessage } from "./client";
import type { VisualizationData } from "../../types/supply-tree";

/** One row of the caller's saved supply-tree history. */
export interface SolutionSummary {
  id: string;
  okh_id: string | null;
  okh_title: string | null;
  facility_name: string | null;
  matching_mode: string | null;
  tree_count: number;
  facility_count: number;
  score: number;
  created_at: string | null;
}

/**
 * List the caller's saved supply-tree solutions, most recent first.
 *
 * Scoped server-side to the account behind the API key in use — this is the
 * condition on which the browse exists at all. It was removed once for
 * listing every visitor's searches out of shared storage, so the endpoint now
 * answers with the caller's own rows and nothing else, and with an empty list
 * when there is no key. There is no query parameter for whose rows to fetch;
 * ownership is read from the credential.
 */
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
  const result =
    (data as { data?: { result?: unknown[] } })?.data?.result ?? [];
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
      errorMessage(
        error,
        `Failed to load visualization (HTTP ${response.status})`,
      ),
    );
  }
  // Bundle is nested under the response envelope's `data`.
  return ((data as { data?: VisualizationData })?.data ??
    data) as VisualizationData;
}

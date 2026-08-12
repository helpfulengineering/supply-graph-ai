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

export interface SolutionStaleness {
  solution_id: string;
  is_stale: boolean;
  staleness_reason: string | null;
  age_days: number | null;
}

/**
 * Whether a saved solution has aged out.
 *
 * Solutions carry a TTL and expire, and nothing in the UI said so — a reader
 * could open one that was about to vanish and have no way to know.
 */
export async function fetchSolutionStaleness(
  solutionId: string,
): Promise<SolutionStaleness> {
  const { data, error, response } = await apiClient.GET(
    "/api/supply-tree/solution/{solution_id}/staleness",
    { params: { path: { solution_id: solutionId } } },
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Could not read staleness (HTTP ${response.status})`),
    );
  }
  const body = (data ?? {}) as Partial<SolutionStaleness> & {
    data?: Partial<SolutionStaleness>;
  };
  const payload = body.data ?? body;
  return {
    solution_id: payload.solution_id ?? solutionId,
    is_stale: payload.is_stale ?? false,
    staleness_reason: payload.staleness_reason ?? null,
    age_days: payload.age_days ?? null,
  };
}

/** Keep a solution for another `days`. The action a staleness banner offers. */
export async function extendSolutionTtl(
  solutionId: string,
  days: number,
): Promise<void> {
  const { error, response } = await apiClient.POST(
    "/api/supply-tree/solution/{solution_id}/extend",
    {
      params: { path: { solution_id: solutionId } },
      body: {
        additional_days: days,
        // From the shared request base and meaningless here; required by the
        // schema, so sent as null rather than omitted.
        quality_level: null,
        strict_mode: null,
      },
    },
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(
        error,
        `Could not extend the solution (HTTP ${response.status})`,
      ),
    );
  }
}

export interface SolutionHierarchy {
  root_components: string[];
  component_details: Record<string, unknown>;
  summary: {
    total_components?: number;
    root_components?: number;
    total_trees?: number;
    max_depth?: number;
  };
}

/**
 * Component parent/child structure.
 *
 * The one supply-tree read that adds data the visualization bundle does not
 * carry — it has the production sequence and the dependency graph, but no
 * hierarchy.
 */
export async function fetchSolutionHierarchy(
  solutionId: string,
): Promise<SolutionHierarchy> {
  const { data, error, response } = await apiClient.GET(
    "/api/supply-tree/solution/{solution_id}/hierarchy",
    { params: { path: { solution_id: solutionId } } },
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(
        error,
        `Could not read the hierarchy (HTTP ${response.status})`,
      ),
    );
  }
  const body = (data ?? {}) as Record<string, unknown>;
  const payload = (body.data as Record<string, unknown>) ?? body;
  return {
    root_components: (payload.root_components as string[]) ?? [],
    component_details:
      (payload.component_details as Record<string, unknown>) ?? {},
    summary: (payload.summary as SolutionHierarchy["summary"]) ?? {},
  };
}

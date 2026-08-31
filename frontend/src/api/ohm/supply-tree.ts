import { z } from "zod";
import { apiClient, ApiError, errorMessage } from "./client";
import { parsePayload } from "./parse";
import type { components } from "../generated/schema";
import type { VisualizationData } from "../../types/supply-tree";

/** One row of the caller's saved supply-tree history. */
export type SolutionSummary = components["schemas"]["SolutionListRow"];

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
  return data?.data?.result ?? [];
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
  if (!data?.data) {
    throw new ApiError(response.status, "Visualization response had no body");
  }
  return data.data;
}

export type SolutionStaleness = components["schemas"]["SolutionStalenessData"];

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

/** A top-level component in a solution's hierarchy — an object, not an id. */
export type RootComponent = components["schemas"]["RootComponentRef"];

/** The hierarchy payload, as the route's response model declares it. */
export type SolutionHierarchy = components["schemas"]["SolutionHierarchyData"];

/**
 * Runtime shape check for the fields this app reads.
 *
 * `looseObject` throughout, deliberately. A plain `z.object` strips keys it
 * does not declare, which would rebuild — at the client, one layer down — the
 * very filtering hazard that makes `response_model` dangerous to write by
 * hand. Nothing here may remove a field the server sent.
 *
 * Only the fields the UI actually renders are described. The point is to name
 * the endpoint and field when a drift arrives, not to restate the whole
 * generated type in a second place that can itself go stale.
 */
const HIERARCHY_PATH = "/api/supply-tree/solution/{solution_id}/hierarchy";

const hierarchySchema = z.looseObject({
  root_components: z.array(
    z.looseObject({
      component_id: z.string(),
      component_name: z.string(),
      tree_id: z.string(),
    }),
  ),
  component_details: z.record(z.string(), z.unknown()),
  summary: z.looseObject({
    total_components: z.number(),
    root_components: z.number(),
    total_trees: z.number(),
    max_depth: z.number(),
  }),
});

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
  const { data, error, response } = await apiClient.GET(HIERARCHY_PATH, {
    params: { path: { solution_id: solutionId } },
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(
        error,
        `Could not read the hierarchy (HTTP ${response.status})`,
      ),
    );
  }
  // The widening is the one assertion left, and it is a much smaller one than
  // the cast it replaces. The schema deliberately describes only what the UI
  // reads, so its inferred type is narrower than the contract; the rest of the
  // type comes from codegen, generated from the server's own schema, rather
  // than from someone reading the route and guessing.
  return parsePayload(
    HIERARCHY_PATH,
    hierarchySchema,
    data?.data,
  ) as SolutionHierarchy;
}

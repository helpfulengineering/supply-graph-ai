/**
 * Supply tree / visualization types.
 *
 * Generated from the API schema (#373). These were hand-written against a
 * fixture, and had drifted: `estimated_time` and `total_estimated_time` were
 * declared `number | null`, but the API returns a string — "3 days", a critical
 * path duration, not a quantity. Anything doing arithmetic on them was working
 * from a type the server never honoured.
 *
 * The names are kept as they were so callers do not churn; only the
 * definitions moved to the schema.
 */
import type { components } from "../api/generated/schema";

export type VisualizationNode = components["schemas"]["VisualizationNode"];
export type VisualizationEdge = components["schemas"]["VisualizationEdge"];
export type SupplyTree = components["schemas"]["VisualizationSupplyTree"];
export type VisualizationData =
  components["schemas"]["VisualizationBundleData"];
export type VisualizationResponse =
  components["schemas"]["SolutionVisualizationResponse"];
export type SolutionListItem = components["schemas"]["SolutionListRow"];

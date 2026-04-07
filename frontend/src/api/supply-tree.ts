import { get } from "./client";
import type { VisualizationResponse, SolutionSummary } from "../types/supply-tree";
import type { ApiEnvelope } from "../types/api";

export function fetchVisualization(solutionId: string): Promise<VisualizationResponse> {
  return get<VisualizationResponse>(`/supply-tree/solution/${solutionId}/visualization`);
}

export function fetchSolutionSummary(solutionId: string): Promise<ApiEnvelope<SolutionSummary>> {
  return get<ApiEnvelope<SolutionSummary>>(`/supply-tree/solution/${solutionId}/summary`);
}

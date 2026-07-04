import { apiBaseUrl, apiClient, ApiError, errorMessage } from "./client";

export interface RunMatchParams {
  okhId: string;
  maxResults?: number;
  qualityLevel?: string;
  strictMode?: boolean;
  /** Restrict matching to these facility IDs; empty/undefined means all. */
  okwIds?: string[];
}

export interface RawSolution {
  facility_id?: string | null;
  facility_name?: string | null;
  confidence?: number;
  score?: number;
  rank?: number;
  explanation_human?: string | null;
  match_type?: string | null;
  tree?: { id?: string | null } | null;
}

export interface RawMatchData {
  solutions?: RawSolution[];
  coverage_gaps?: string[];
  human_summary?: { executive?: string; technical?: string } | null;
  match_summary_text?: string | null;
  total_solutions?: number;
  suggestions?: string[];
  /** Present when save_solution was requested — the persisted solution's id. */
  solution_id?: string | null;
}

export interface RawMatchResponse {
  data?: RawMatchData;
}

/** Run a domain-aware match for an OKH design; returns the raw envelope. */
export async function runMatch(params: RunMatchParams): Promise<RawMatchResponse> {
  const { data, error, response } = await apiClient.POST("/api/match", {
    // The generated schema marks many match-request fields as required, but the
    // API defaults them server-side; the minimal set below is what the endpoint
    // needs (verified against the live endpoint). Cast to satisfy the strict
    // generated body type without enumerating server-defaulted fields.
    body: {
      okh_id: params.okhId,
      max_results: params.maxResults ?? 10,
      include_human_summary: true,
      include_explanation: true,
      // Persist the solution so it has an id the supply-tree explorer can load.
      save_solution: true,
      quality_level: params.qualityLevel,
      strict_mode: params.strictMode,
      // Omit when empty so the server matches against all facilities.
      ...(params.okwIds && params.okwIds.length > 0
        ? { okw_ids: params.okwIds }
        : {}),
    } as never,
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Match failed (HTTP ${response.status})`),
    );
  }
  return (data ?? {}) as RawMatchResponse;
}

/** A design a facility can produce (reverse-match result row). */
export interface FacilityDesign {
  okh_id: string;
  okh_title: string | null;
  confidence: number;
  rank: number;
}

export interface FacilityDesignsResult {
  facility_name: string | null;
  designs: FacilityDesign[];
  total_designs: number;
}

/**
 * Reverse match: the designs a facility can produce, ranked by confidence.
 *
 * Uses a raw fetch (not the generated client) because POST /api/match/facility
 * is newer than the committed OpenAPI schema; swap to `apiClient` once the
 * schema is regenerated. Goes through globalThis.fetch so MSW still intercepts.
 */
export async function fetchDesignsForFacility(
  okwId: string,
  opts: { minConfidence?: number; maxResults?: number } = {},
): Promise<FacilityDesignsResult> {
  const response = await globalThis.fetch(`${apiBaseUrl}/api/match/facility`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      okw_id: okwId,
      min_confidence: opts.minConfidence ?? 0.1,
      max_results: opts.maxResults ?? 10,
    }),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(body, `Failed to load producible designs (HTTP ${response.status})`),
    );
  }
  const data = (body as { data?: Partial<FacilityDesignsResult> })?.data ?? {};
  return {
    facility_name: data.facility_name ?? null,
    designs: (data.designs ?? []) as FacilityDesign[],
    total_designs: data.total_designs ?? (data.designs?.length ?? 0),
  };
}

import { apiBaseUrl, apiClient, ApiError, errorMessage, requestIdFromError } from "./client";

export interface RunMatchParams {
  /** Catalogue design id. Omit when matching an inline manifest. */
  okhId?: string;
  /**
   * A full OKH manifest to match directly, without it being in the catalogue.
   *
   * This is what lets a design generated from a repository URL be matched
   * immediately: generation deliberately does not save (no accounts means no
   * owner or provenance), so there is no id to match by. The API accepts
   * `okh_manifest` as an alternative to `okh_id`.
   */
  okhManifest?: Record<string, unknown>;
  maxResults?: number;
  qualityLevel?: string;
  strictMode?: boolean;
  /** Restrict matching to these facility IDs; empty/undefined means all. */
  okwIds?: string[];
  /** Match against the filtered network (local ∪ MoM); supersedes okwIds. */
  networkFilter?: Record<string, string | boolean>;
}

export interface RawSolution {
  facility_id?: string | null;
  facility_name?: string | null;
  confidence?: number;
  score?: number;
  rank?: number;
  explanation_human?: string | null;
  /** Structured explanation; carries per-requirement match status. */
  explanation?: {
    requirement_matches?:
      | { status?: string | null; requirement_value?: string | null }[]
      | null;
    missing_capabilities?: unknown[] | null;
    overall_status?: string | null;
    /** Mean of the per-requirement confidences; see matchViewModel. */
    overall_confidence?: number | null;
  } | null;
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
  // The API requires exactly one of okh_id / okh_manifest / okh_url and 422s
  // with "Must provide either..." when given none — reachable from the UI, and
  // opaque by the time it reaches a toast. Guarded here.
  //
  // Deliberately NOT also checking that okh_id is a UUID: the deployed API
  // parses it as one, but that is the server's rule to enforce. Duplicating it
  // here rejects instances whose ids are shaped differently (the mocked lane,
  // for one) and puts the client in the business of guessing the server's
  // schema. A server that rejects the id says so, and formatValidationError
  // below makes that answer readable.
  if (!params.okhManifest && !params.okhId) {
    throw new ApiError(400, "Select a design before running a match.");
  }

  const { data, error, response } = await apiClient.POST("/api/match", {
    // The generated schema marks many match-request fields as required, but the
    // API defaults them server-side; the minimal set below is what the endpoint
    // needs (verified against the live endpoint). Cast to satisfy the strict
    // generated body type without enumerating server-defaulted fields.
    body: {
      // Exactly one of these carries the design; the API accepts either.
      ...(params.okhManifest
        ? { okh_manifest: params.okhManifest }
        : { okh_id: params.okhId }),
      max_results: params.maxResults ?? 10,
      include_human_summary: true,
      include_explanation: true,
      // Persist the solution so it has an id the supply-tree explorer can load.
      // Not for inline manifests: the design itself is deliberately unsaved, so
      // a stored solution would reference an OKH id that does not exist. The
      // trade is that inline matches have no supply-tree deep link.
      save_solution: !params.okhManifest,
      quality_level: params.qualityLevel,
      strict_mode: params.strictMode,
      // Network match (local ∪ MoM) can combine with an explicit id subset.
      ...(params.networkFilter ? { network_filter: params.networkFilter } : {}),
      ...(params.okwIds && params.okwIds.length > 0
        ? { okw_ids: params.okwIds }
        : {}),
    } as never,
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Match failed (HTTP ${response.status})`),
      requestIdFromError(error, response),
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
      requestIdFromError(body, response),
    );
  }
  const data = (body as { data?: Partial<FacilityDesignsResult> })?.data ?? {};
  return {
    facility_name: data.facility_name ?? null,
    designs: (data.designs ?? []) as FacilityDesign[],
    total_designs: data.total_designs ?? (data.designs?.length ?? 0),
  };
}

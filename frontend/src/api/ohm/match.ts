import { apiClient, ApiError, errorMessage } from "./client";

export interface RunMatchParams {
  okhId: string;
  maxResults?: number;
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

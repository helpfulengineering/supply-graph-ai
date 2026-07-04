import type { RawMatchResponse } from "../../api/ohm/match";

/**
 * Match view-model (pure, unit-tested) — module 2 of the architecture.
 *
 * Narrows the raw match envelope into a ranked, presentation-ready view:
 * solutions sorted by confidence (then rank), the plain-language summary,
 * coverage gaps, and a total. No React.
 */

export interface RankedSolution {
  facilityName: string;
  facilityId: string | null;
  confidence: number;
  score: number;
  rank: number;
  explanation: string | null;
}

export interface MatchView {
  solutions: RankedSolution[];
  coverageGaps: string[];
  summary: string | null;
  totalSolutions: number;
  /** Persisted solution id for hand-off into the supply-tree explorer. */
  solutionId: string | null;
}

export function toMatchView(raw: RawMatchResponse): MatchView {
  const data = raw.data ?? {};
  const solutions: RankedSolution[] = (data.solutions ?? [])
    .map((s) => ({
      facilityName: s.facility_name ?? "Unknown facility",
      facilityId: s.facility_id ?? null,
      confidence: s.confidence ?? 0,
      score: s.score ?? 0,
      rank: s.rank ?? 0,
      explanation: s.explanation_human ?? null,
    }))
    .sort((a, b) => b.confidence - a.confidence || a.rank - b.rank);

  return {
    solutions,
    coverageGaps: data.coverage_gaps ?? [],
    summary: data.human_summary?.executive ?? data.match_summary_text ?? null,
    totalSolutions: data.total_solutions ?? solutions.length,
    solutionId: data.solution_id ?? null,
  };
}

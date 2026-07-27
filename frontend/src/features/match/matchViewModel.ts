import type { RawMatchResponse } from "../../api/ohm/match";

/**
 * Match view-model (pure, unit-tested) — module 2 of the architecture.
 *
 * Narrows the raw match envelope into a ranked, presentation-ready view:
 * solutions sorted by confidence (then rank), the plain-language summary,
 * coverage gaps, and a total. No React.
 */

import { requirementStats, type RequirementStats } from "./nearMiss";

export interface RankedSolution {
  facilityName: string;
  facilityId: string | null;
  confidence: number;
  score: number;
  rank: number;
  explanation: string | null;
  /** Per-solution supply-tree id when the API returned one on the solution. */
  treeId: string | null;
  /**
   * Requirement coverage from the structured explanation. Null when the API
   * did not supply one — which must not be read as "nothing missing".
   */
  coverage: RequirementStats | null;
}

export interface MatchView {
  solutions: RankedSolution[];
  coverageGaps: string[];
  summary: string | null;
  totalSolutions: number;
  /**
   * Persisted solution id — what the supply-tree explorer loads.
   *
   * Null when the match was not saved (inline manifests), in which case no card
   * offers a tree link. `treeId` identifies a tree WITHIN this solution and is
   * not addressable on its own.
   */
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
      treeId: s.tree?.id ?? null,
      coverage: requirementStats(
        s.explanation as Parameters<typeof requirementStats>[0],
      ),
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

/** Stable key for selecting a ranked solution in the UI. */
export function solutionSelectionKey(s: RankedSolution, index: number): string {
  return s.facilityId ?? s.treeId ?? `rank-${s.rank}-${index}`;
}

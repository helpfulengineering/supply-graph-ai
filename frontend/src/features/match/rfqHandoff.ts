import type { MatchSolution } from "../../types/match";
import type { RankedSolution } from "./matchViewModel";

/**
 * Build the RFQ navigation payload from selected match results.
 * Contact/location are sparse until facility detail is loaded on the RFQ page;
 * website is filled when we already know a network URL (e.g. Maps of Making).
 */
export function toRfqSolutions(
  selected: RankedSolution[],
  websiteByFacilityId: Record<string, string | null | undefined> = {},
): MatchSolution[] {
  return selected.map((s) => {
    const website =
      (s.facilityId && websiteByFacilityId[s.facilityId]) || undefined;
    return {
      facility_id: s.facilityId ?? "",
      facility_name: s.facilityName,
      confidence: s.confidence,
      score: s.score,
      rank: s.rank,
      match_type: "direct",
      explanation: null,
      explanation_human: s.explanation,
      metrics: {
        facility_count: 1,
        requirement_count: 0,
        capability_count: 0,
      },
      tree: {
        id: s.treeId ?? s.facilityId ?? `rank-${s.rank}`,
        facility_name: s.facilityName,
        okh_reference: "",
        confidence_score: s.confidence,
        estimated_cost: null,
        estimated_time: null,
        match_type: "direct",
        depth: 0,
        production_stage: "",
        metadata: {},
      },
      facility: {
        id: s.facilityId ?? "",
        name: s.facilityName,
        location: { city: "", country: "" },
        manufacturing_processes: [],
        contact: website ? { website } : undefined,
      },
    };
  });
}

import type { Facility, MatchSolution } from "../../types/match";
import type { RankedSolution } from "./matchViewModel";

/**
 * Build the RFQ navigation payload from selected match results.
 *
 * The facility travels as the API returned it. This used to synthesise a hollow
 * one — `location: { city: "", country: "" }`, no contact — on the stated
 * assumption that "contact/location are sparse until facility detail is loaded
 * on the RFQ page". That load was never built, so every generated RFQ went out
 * reading "Location not specified" with no way to reach the facility it was
 * addressed to, while the full OKW record sat unused in the match response
 * (#501).
 *
 * `websiteByFacilityId` still has a job: Maps-of-Making rows carry a URL that
 * their projected facility record does not, so it fills that gap and nothing
 * else.
 */
export function toRfqSolutions(
  selected: RankedSolution[],
  websiteByFacilityId: Record<string, string | null | undefined> = {},
): MatchSolution[] {
  return selected.map((s) => ({
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
    // Cast once, here. `Facility` is the app's view type and what the API
    // returns is an OKW document; they agree on the fields RFQ reads and
    // disagree on optionality, and the server takes Dict[str, Any] regardless.
    facility: facilityFor(s, websiteByFacilityId) as unknown as Facility,
  }));
}

/** The API's facility when there is one, with a known network URL filled in. */
function facilityFor(
  s: RankedSolution,
  websiteByFacilityId: Record<string, string | null | undefined>,
): Record<string, unknown> {
  const website =
    (s.facilityId && websiteByFacilityId[s.facilityId]) || undefined;
  const base =
    s.facility ??
    // No facility on the solution at all: name it, and leave the rest absent
    // rather than asserting empty strings that read as "known to be blank".
    ({
      id: s.facilityId ?? "",
      name: s.facilityName,
      manufacturing_processes: [],
    } as Record<string, unknown>);

  if (!website) return base;

  const agent = (base.contact as Record<string, unknown> | undefined) ?? {};
  if (agent.website) return base;
  return { ...base, contact: { ...agent, website } };
}

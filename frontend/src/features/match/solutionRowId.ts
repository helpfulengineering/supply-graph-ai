import type { MatchSolution } from "../../types/match";

/**
 * Unique row identity for list keys and checkbox selection.
 * The API can return several solutions with the same `facility_id` (e.g. alternate
 * trees); using only `facility_id` collides in React and breaks per-row selection.
 */
export function solutionRowId(sol: MatchSolution): string {
  const tid = sol.tree?.id;
  if (tid != null && String(tid).trim() !== "") return String(tid);
  return `${sol.facility_id}#${sol.rank}`;
}

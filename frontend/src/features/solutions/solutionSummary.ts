import type { SolutionSummary } from "../../api/ohm/supply-tree";

/**
 * How a saved solution presents itself in a list.
 *
 * Its own module, like supplyTreeAdapter and deriveFilterOptions: these are
 * pure and worth testing without rendering anything, and exporting them beside
 * the component would put non-component exports in a component file.
 */

/**
 * A solution's display name.
 *
 * Falls through title → short id → a generic label, because okh_title is only
 * populated when the match ran against a catalogue design. A pasted or
 * generated manifest produces a solution with no title at all.
 */
export function solutionLabel(solution: SolutionSummary): string {
  if (solution.okh_title) return solution.okh_title;
  if (solution.okh_id) return `${solution.okh_id.slice(0, 8)}…`;
  return "Untitled solution";
}

/**
 * Score as a whole percentage, or null when there is none.
 *
 * Null rather than 0 so the caller can drop the badge: a missing score
 * rendered as "0%" reads as a scored-and-failed match, which is a different
 * claim from "not scored".
 */
export function scorePercent(score: number | null | undefined): number | null {
  if (typeof score !== "number" || Number.isNaN(score)) return null;
  return Math.round(score * 100);
}

/** Locale date, or "" when the timestamp is absent or unparseable. */
export function formatSaved(created_at: string | null | undefined): string {
  if (!created_at) return "";
  const date = new Date(created_at);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString();
}

/** Hue by score band — the same thresholds the match results use. */
export function scoreVariant(percent: number): "green" | "yellow" | "red" {
  if (percent >= 80) return "green";
  if (percent >= 50) return "yellow";
  return "red";
}

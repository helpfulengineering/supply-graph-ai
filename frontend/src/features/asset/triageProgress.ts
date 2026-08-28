/**
 * "8 of 12 components assessed" — one figure and one sentence, computed once.
 *
 * Shared by the list row, the detail header and the triage page, because three
 * places phrasing the same fact three ways is how "never triaged" ends up
 * rendering as "0 of 0" on one of them.
 */
import type { AssetResponse, ComponentState } from "@/api/ohm/asset";
import { componentStates } from "@/api/ohm/asset";

export interface TriageProgress {
  assessed: number;
  total: number;
  /** Null when the total is unknown — see `fromAsset`. */
  fraction: number | null;
  /** "8 of 12 assessed", or "never triaged". */
  label: string;
}

export function triageProgress(
  assessed: number,
  total: number,
): TriageProgress {
  if (total <= 0) {
    return {
      assessed,
      total,
      fraction: null,
      label: assessed > 0 ? `${assessed} assessed` : "never triaged",
    };
  }
  return {
    assessed,
    total,
    fraction: assessed / total,
    label: `${assessed} of ${total} assessed`,
  };
}

/**
 * Progress from an asset record alone.
 *
 * An asset carries the observations it has, not the manifest's component list,
 * so the denominator is genuinely unknown here — only the checklist knows how
 * many components the design has. Reporting `n of n` from the observations
 * would claim a complete triage for a unit where one component was looked at.
 * `total: 0` is that ignorance, and `triageProgress` renders it as a bare
 * count.
 */
export function progressFromAsset(asset: AssetResponse): TriageProgress {
  const states: ComponentState[] = componentStates(asset);
  const assessed = states.filter(
    (s) => s.condition && s.condition !== "unknown",
  ).length;
  return triageProgress(assessed, 0);
}

/** How long ago the unit was last triaged, or null if it never was. */
export function lastTriagedLabel(
  lastTriagedAt: string | null | undefined,
  now: number,
): string | null {
  if (!lastTriagedAt) return null;
  const at = Date.parse(lastTriagedAt);
  if (Number.isNaN(at)) return null;
  const days = Math.floor((now - at) / 86_400_000);
  if (days <= 0) return "triaged today";
  if (days === 1) return "triaged yesterday";
  return `triaged ${days} days ago`;
}

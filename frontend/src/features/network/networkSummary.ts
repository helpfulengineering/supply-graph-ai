import type { NetworkData } from "../../api/ohm/network";

export const SOURCE_STYLES = {
  local: { color: "#4f46e5", label: "OHM facilities" },
  mom: { color: "#0d9488", label: "Maps of Making" },
} as const;

/**
 * Human-readable one-line summary of the network's point set (pure, unit-tested).
 * Communicates coverage + the two graceful-degradation cases: local facilities
 * dropped for missing coordinates, and MoM being unavailable.
 */
export function buildNetworkSummary(
  data: Pick<NetworkData, "local_count" | "mom_count" | "dropped_no_coords" | "mom_available">,
): string {
  const n = (v: number) => v.toLocaleString();
  const parts = [`${n(data.local_count)} OHM ${data.local_count === 1 ? "facility" : "facilities"}`];
  if (data.mom_available) {
    parts.push(`${n(data.mom_count)} Maps of Making spaces`);
  }
  let summary = parts.join(" · ");
  if (data.dropped_no_coords > 0) {
    summary += ` · ${n(data.dropped_no_coords)} without coordinates not shown`;
  }
  if (!data.mom_available) {
    summary += " · Maps of Making unavailable — showing local only";
  }
  return summary;
}

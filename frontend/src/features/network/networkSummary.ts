import type { NetworkData } from "../../api/ohm/network";

// Source hues come from the world's chart ramp, resolved at call time —
// leaflet div-icons are HTML strings and CSS custom properties do not survive
// the inline style, so the map reads concrete values like the canvas renderers.
export const SOURCE_STYLES = {
  local: { token: "--chart-1", label: "OHM facilities" },
  mom: { token: "--chart-2", label: "Maps of Making" },
} as const;

export type NetworkSource = keyof typeof SOURCE_STYLES;

export function sourceColor(source: NetworkSource): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement)
    .getPropertyValue(SOURCE_STYLES[source].token)
    .trim();
}

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

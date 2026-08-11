import type { NetworkData } from "../../api/ohm/network";

// Source hues come from the world's chart ramp.
export const SOURCE_STYLES = {
  local: { token: "--chart-1", label: "OHM facilities" },
  mom: { token: "--chart-2", label: "Maps of Making" },
} as const;

export type NetworkSource = keyof typeof SOURCE_STYLES;

/**
 * The source's colour as a var() the browser resolves, for anything that ends
 * up in the DOM — which includes leaflet div-icons.
 *
 * The icons were built from `sourceColor` on the reasoning that a div-icon is
 * an HTML string and could not carry a custom property. It can: the string
 * becomes real elements inside the marker pane, and a custom property inherits
 * down to them like any other. The two `var()`s already in the cluster bubble
 * (--card, --ttm-on-accent) were the standing counter-example.
 *
 * The difference is the whole cost of a theme change on this page. A concrete
 * colour is baked at build time, so the world changing meant rebuilding 3,202
 * markers and the cluster tree with it — in an effect, a frame or two after
 * everything else had already changed, which is exactly the lag a reader sees
 * as the map catching up. Through a var() the same markers repaint from the
 * cascade, with no JavaScript, no React, and nothing to rebuild.
 */
export function sourceVar(source: NetworkSource): string {
  return `var(${SOURCE_STYLES[source].token})`;
}

/** The same hue as a concrete value, for canvas renderers that cannot use var(). */
export function sourceColor(source: NetworkSource): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement)
    .getPropertyValue(SOURCE_STYLES[source].token)
    .trim();
}

/**
 * The ink for spaces the map cannot plot — the ones with no coordinates.
 *
 * They are in the counts and nowhere on the map, which is the one thing a
 * reader cannot work out from looking at it. A key entry in a colour that
 * appears nowhere else says "these exist and are not here", which is honest;
 * giving them a marker would not be.
 *
 * Kept beside `sourceColor` because the map and the legend must not be able to
 * disagree about a colour.
 */
export function unplottedColor(): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement)
    .getPropertyValue("--ttm-text-secondary")
    .trim();
}

/** The unplotted ink as a var(), for the DOM. See `sourceVar`. */
export const UNPLOTTED_VAR = "var(--ttm-text-secondary)";

/**
 * Human-readable one-line summary of the network's point set (pure, unit-tested).
 * Communicates coverage + the two graceful-degradation cases: local facilities
 * dropped for missing coordinates, and MoM being unavailable.
 */
export function buildNetworkSummary(
  data: Pick<
    NetworkData,
    "local_count" | "mom_count" | "dropped_no_coords" | "mom_available"
  >,
): string {
  const n = (v: number) => v.toLocaleString();
  const parts = [
    `${n(data.local_count)} OHM ${data.local_count === 1 ? "facility" : "facilities"}`,
  ];
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

import type { NetworkSpace } from "../../api/ohm/network";

/**
 * Dashboard statistics, derived from the network set the map already loaded.
 *
 * Pure and exported so they are unit-testable without a chart or a render, and
 * so the charts stay dumb: they receive rows and draw them.
 *
 * Deriving from the loaded set rather than adding endpoints is the point —
 * the dashboard already holds every space, so a "where is the network" chart
 * costs one pass over an array rather than a round trip.
 */

export interface Row {
  /** What the axis reads: a country name, a capability in words. */
  label: string;
  value: number;
  /**
   * The value the network filter takes for this row — a country name, a
   * canonical process id. Kept alongside the label because the two diverge
   * (the axis says "cnc machining"; the filter wants `cnc_machining`), and a
   * chart that links to the filtered network needs the latter.
   */
  key: string;
}

function topBy<T>(
  items: T[],
  key: (item: T) => string | null | undefined,
  limit: number | undefined,
  label: (key: string) => string = (k) => k,
): Row[] {
  const counts = new Map<string, number>();
  for (const item of items) {
    const k = key(item);
    if (!k) continue;
    counts.set(k, (counts.get(k) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([k, value]) => ({ key: k, label: label(k), value }))
    .sort((a, b) => b.value - a.value || a.label.localeCompare(b.label))
    .slice(0, limit);
}

/** Where the network is. Every country by default — the tail is the point. */
export function facilitiesByCountry(
  spaces: NetworkSpace[],
  limit?: number,
): Row[] {
  return topBy(spaces, (s) => s.country, limit);
}

/**
 * What the network can make.
 *
 * A space lists several processes, so this counts memberships rather than
 * spaces: the totals deliberately exceed the facility count, because the
 * question is "how much capacity exists for this capability", not "how many
 * facilities are there".
 */
export function capabilityCoverage(
  spaces: NetworkSpace[],
  limit?: number,
): Row[] {
  const counts = new Map<string, number>();
  for (const space of spaces) {
    for (const process of space.processes ?? []) {
      if (!process) continue;
      counts.set(process, (counts.get(process) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    // Stored as slugs (cnc_machining); the axis reads better in words.
    .map(([key, value]) => ({ key, label: key.replace(/[_-]+/g, " ").trim(), value }))
    .filter((r) => r.label)
    .sort((a, b) => b.value - a.value || a.label.localeCompare(b.label))
    .slice(0, limit);
}

/** Local records versus federated ones — the two-source story the map tells. */
export function spacesBySource(spaces: NetworkSpace[]): Row[] {
  return topBy(spaces, (s) => s.source, 2, (k) =>
    k === "local" ? "OHM facilities" : "Maps of Making",
  );
}

/**
 * Sourcing resolution, split the way a coordinator acts on it.
 *
 * The server returns one flat list with a `verdict` per item. Two verdicts mean
 * two different next actions — claim a part that already exists somewhere, or
 * go and buy one — so they are two sections rather than one list with a badge.
 */
import type { SourcingItem, SourcingResolution } from "@/api/ohm/asset";
import { sourcingMatches } from "@/api/ohm/asset";
import type { SalvageMatchItem } from "@/api/ohm/asset";

export interface SourcingRow {
  item: SourcingItem;
  matches: SalvageMatchItem[];
}

export interface SourcingSplit {
  fleetAvailable: SourcingRow[];
  procureNew: SourcingRow[];
  /** True when triage has produced nothing to source. */
  empty: boolean;
}

/** Verdict string the backend uses for "another unit has one". */
const FLEET_AVAILABLE = "fleet_available";

export function splitSourcing(resolution: SourcingResolution): SourcingSplit {
  const rows: SourcingRow[] = (resolution.items ?? []).map((item) => ({
    item,
    matches: sourcingMatches(item),
  }));
  const fleetAvailable = rows.filter(
    (row) => row.item.verdict === FLEET_AVAILABLE,
  );
  const procureNew = rows.filter((row) => row.item.verdict !== FLEET_AVAILABLE);
  return { fleetAvailable, procureNew, empty: rows.length === 0 };
}

/**
 * Why the sourcing button is disabled, or null when it is not.
 *
 * Resolution is expensive — a fleet-wide scan per component needing a part —
 * and meaningless before triage, so the page says which of those it is rather
 * than presenting a control that does nothing.
 */
export function sourcingUnavailableReason(
  lastTriagedAt: string | null | undefined,
  sourceNewCount: number | null,
): string | null {
  if (!lastTriagedAt)
    return "Run triage first — sourcing works from its results.";
  if (sourceNewCount === 0) return "Triage found no components needing a part.";
  return null;
}

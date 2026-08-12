/**
 * The asset lifecycle, as data.
 *
 * Ordered by the life of a unit rather than alphabetically, because that is the
 * order a queue should read in: a fleet list grouped alphabetically opens on
 * "condemned", which is the one group nobody is working on.
 *
 * Each status carries what it MEANS, not just a label. The word "restored"
 * tells a technician nothing about whether it is theirs to set; the sentence
 * does, and it is rendered under the control that sets it.
 */

export type AssetStatus =
  | "active"
  | "under_triage"
  | "parts_pending"
  | "under_repair"
  | "restored"
  | "condemned";

export interface AssetStatusInfo {
  value: AssetStatus;
  label: string;
  /** One line, in the second person, stating when this status is the true one. */
  meaning: string;
  /** Badge hue. Named for the hue, per Badge's own convention. */
  tone: "default" | "green" | "yellow" | "red" | "blue" | "indigo";
}

export const ASSET_STATUSES: readonly AssetStatusInfo[] = [
  {
    value: "active",
    label: "Active",
    meaning: "In service. Nothing is known to be wrong with it.",
    tone: "green",
  },
  {
    value: "under_triage",
    label: "Under triage",
    meaning: "Someone is assessing it now, component by component.",
    tone: "blue",
  },
  {
    value: "parts_pending",
    label: "Parts pending",
    meaning: "Triaged, and waiting on parts before repair can start.",
    tone: "yellow",
  },
  {
    value: "under_repair",
    label: "Under repair",
    meaning: "Parts are in hand and the work is under way.",
    tone: "indigo",
  },
  {
    value: "restored",
    label: "Restored",
    meaning: "Repaired and back in service.",
    tone: "green",
  },
  {
    value: "condemned",
    label: "Condemned",
    meaning:
      "Beyond repair. Still worth keeping listed — its parts may be harvestable.",
    tone: "red",
  },
] as const;

const BY_VALUE = new Map(ASSET_STATUSES.map((s) => [s.value, s]));

/** Narrow a status string from the API or the URL, or null if unrecognised. */
export function parseAssetStatus(
  raw: string | null | undefined,
): AssetStatus | null {
  if (!raw) return null;
  return BY_VALUE.has(raw as AssetStatus) ? (raw as AssetStatus) : null;
}

/**
 * Display info for a status string.
 *
 * Falls back to showing the raw value rather than hiding it: a status the
 * frontend has not heard of is a backend that moved, and a blank badge would
 * be the frontend deciding not to mention it.
 */
export function assetStatusInfo(
  raw: string | null | undefined,
): AssetStatusInfo {
  const known = parseAssetStatus(raw);
  if (known) return BY_VALUE.get(known)!;
  return {
    value: (raw || "unknown") as AssetStatus,
    label: raw || "Unknown",
    meaning: "Not a status this version of the app knows about.",
    tone: "default",
  };
}

/** Lifecycle order, for sorting groups. Unknown statuses sort last. */
export function assetStatusOrder(raw: string | null | undefined): number {
  const index = ASSET_STATUSES.findIndex((s) => s.value === raw);
  return index === -1 ? ASSET_STATUSES.length : index;
}

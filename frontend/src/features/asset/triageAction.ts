/**
 * What triage recommends doing about a component, as data.
 *
 * Mirrors `TriageAction` in src/core/models/repair.py. The server derives these
 * from the observed condition plus the design's own flags, so a technician
 * never picks one — they read them, which is why each carries the sentence that
 * explains what the server concluded.
 *
 * `order` is the priority a report should read in: the things nobody has looked
 * at first, then the work, then the components that need nothing. A report
 * sorted by component name buries "twelve unassessed" under the alphabet.
 */

export type TriageActionValue =
  | "assess"
  | "decommission"
  | "source_new"
  | "harvest"
  | "repair_in_place"
  | "no_action";

export interface TriageActionInfo {
  value: TriageActionValue;
  label: string;
  meaning: string;
  tone: "default" | "green" | "yellow" | "red" | "blue" | "indigo";
  order: number;
  /** The `TriageSummary` field holding this action's count. */
  summaryKey:
    | "needs_assessment"
    | "decommission"
    | "source_new"
    | "harvest"
    | "repair_in_place"
    | "no_action";
}

export const TRIAGE_ACTIONS: readonly TriageActionInfo[] = [
  {
    value: "assess",
    label: "Needs assessment",
    meaning: "Nobody has recorded a condition for this component yet.",
    tone: "default",
    order: 0,
    summaryKey: "needs_assessment",
  },
  {
    value: "decommission",
    label: "Decommission",
    meaning:
      "Damaged or missing, and the design marks it neither repairable nor replaceable.",
    tone: "red",
    order: 1,
    summaryKey: "decommission",
  },
  {
    value: "source_new",
    label: "Source new",
    meaning: "Replaceable by the design, and no salvage route was found.",
    tone: "yellow",
    order: 2,
    summaryKey: "source_new",
  },
  {
    value: "harvest",
    label: "Harvest",
    meaning: "The design marks it salvageable — take one from another unit.",
    tone: "blue",
    order: 3,
    summaryKey: "harvest",
  },
  {
    value: "repair_in_place",
    label: "Repair in place",
    meaning: "Damaged, and someone judged the repair feasible without a part.",
    tone: "indigo",
    order: 4,
    summaryKey: "repair_in_place",
  },
  {
    value: "no_action",
    label: "No action",
    meaning: "Observed intact.",
    tone: "green",
    order: 5,
    summaryKey: "no_action",
  },
] as const;

const BY_VALUE = new Map(TRIAGE_ACTIONS.map((a) => [a.value, a]));

export function triageActionInfo(
  raw: string | null | undefined,
): TriageActionInfo {
  const known = raw ? BY_VALUE.get(raw as TriageActionValue) : undefined;
  if (known) return known;
  return {
    value: (raw || "assess") as TriageActionValue,
    label: raw || "Unknown",
    meaning: "Not an action this version of the app knows about.",
    tone: "default",
    order: TRIAGE_ACTIONS.length,
    summaryKey: "needs_assessment",
  };
}

/**
 * What a technician observed about one component, as data.
 *
 * Four values, matching `ComponentCondition` on the server. `unknown` is a real
 * option rather than an absence: "I looked and could not tell" is a different
 * observation from "nobody has looked", and the checklist distinguishes them by
 * `assessed` rather than by condition.
 */

export type ComponentCondition = "intact" | "damaged" | "missing" | "unknown";

export interface ConditionInfo {
  value: ComponentCondition;
  label: string;
  tone: "default" | "green" | "yellow" | "red" | "blue" | "indigo";
  /**
   * Whether this observation implies follow-up work.
   *
   * Drives whether the three flags are shown: on an intact component nobody
   * needs to say whether repair is feasible, and asking would be three controls
   * per row for the common case.
   */
  impliesWork: boolean;
}

export const COMPONENT_CONDITIONS: readonly ConditionInfo[] = [
  { value: "intact", label: "Intact", tone: "green", impliesWork: false },
  { value: "damaged", label: "Damaged", tone: "yellow", impliesWork: true },
  { value: "missing", label: "Missing", tone: "red", impliesWork: true },
  { value: "unknown", label: "Unknown", tone: "default", impliesWork: false },
] as const;

const BY_VALUE = new Map(COMPONENT_CONDITIONS.map((c) => [c.value, c]));

export function parseCondition(
  raw: string | null | undefined,
): ComponentCondition | null {
  if (!raw) return null;
  return BY_VALUE.has(raw as ComponentCondition)
    ? (raw as ComponentCondition)
    : null;
}

export function conditionInfo(raw: string | null | undefined): ConditionInfo {
  const known = parseCondition(raw);
  if (known) return BY_VALUE.get(known)!;
  return {
    value: (raw || "unknown") as ComponentCondition,
    label: raw || "Unknown",
    tone: "default",
    impliesWork: false,
  };
}

/** Does this condition warrant asking about repair / harvest / sourcing? */
export function conditionImpliesWork(raw: string | null | undefined): boolean {
  return conditionInfo(raw).impliesWork;
}

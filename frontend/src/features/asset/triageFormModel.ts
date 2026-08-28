/**
 * The triage session: checklist in, request out.
 *
 * Two things here are load-bearing and would be wrong if done the obvious way.
 *
 * The three flags are `Optional[bool]` on the server and `null` is NOT `false`
 * — `_derive_action` fills a null flag from the condition plus the design's own
 * flags, and reads a stated `false` as the technician's judgement. A checkbox
 * cannot express that, so the form carries a tri-state and only shows it where
 * the condition implies work.
 *
 * And only CHANGED rows are submitted. Triage is an upsert that stamps a fresh
 * `observed_at` on every component it receives, so sending the untouched rows
 * back would re-date observations nobody made this session.
 */
import type {
  AssetTriageRequest,
  ChecklistItem,
  TriageChecklist,
} from "@/api/ohm/asset";
import type { ComponentCondition } from "./componentCondition";
import { conditionImpliesWork, parseCondition } from "./componentCondition";

/** null means "not stated", which is a third value and not a default. */
export type TriState = boolean | null;

export interface TriageRowState {
  componentName: string;
  condition: ComponentCondition | null;
  repairFeasible: TriState;
  harvestViable: TriState;
  sourceRequired: TriState;
  notes: string;
}

export interface TriageFormState {
  rows: TriageRowState[];
  assessedBy: string;
  sessionNotes: string;
}

function rowFromItem(item: ChecklistItem): TriageRowState {
  const current = (item.current_state ?? {}) as Record<string, unknown>;
  const asTri = (value: unknown): TriState =>
    typeof value === "boolean" ? value : null;
  return {
    componentName: item.component_name,
    condition: parseCondition(item.current_condition),
    repairFeasible: asTri(current.repair_feasible),
    harvestViable: asTri(current.harvest_viable),
    sourceRequired: asTri(current.source_required),
    notes: typeof current.notes === "string" ? current.notes : "",
  };
}

/**
 * `sessionNotes` seeds from the asset's existing triage notes rather than the
 * checklist, which does not carry them: recording again REPLACES the notes on
 * the record, so starting from blank would silently delete the last session's.
 */
export function formStateFromChecklist(
  checklist: TriageChecklist,
  { assessedBy = "", sessionNotes = "" } = {},
): TriageFormState {
  return {
    rows: (checklist.items ?? []).map(rowFromItem),
    assessedBy,
    sessionNotes,
  };
}

export function updateRow(
  state: TriageFormState,
  componentName: string,
  patch: Partial<TriageRowState>,
): TriageFormState {
  return {
    ...state,
    rows: state.rows.map((row) =>
      row.componentName === componentName ? { ...row, ...patch } : row,
    ),
  };
}

/**
 * Setting a condition that implies no work clears the flags back to "not
 * stated".
 *
 * Otherwise a row marked damaged, flagged, then corrected to intact would
 * submit `repair_feasible: true` on an intact component — a claim the
 * technician made about a different observation, left behind by the correction.
 */
export function setCondition(
  state: TriageFormState,
  componentName: string,
  condition: ComponentCondition,
): TriageFormState {
  const patch: Partial<TriageRowState> = { condition };
  if (!conditionImpliesWork(condition)) {
    patch.repairFeasible = null;
    patch.harvestViable = null;
    patch.sourceRequired = null;
  }
  return updateRow(state, componentName, patch);
}

function rowsEqual(a: TriageRowState, b: TriageRowState): boolean {
  return (
    a.condition === b.condition &&
    a.repairFeasible === b.repairFeasible &&
    a.harvestViable === b.harvestViable &&
    a.sourceRequired === b.sourceRequired &&
    a.notes.trim() === b.notes.trim()
  );
}

/** Rows whose observation differs from what the checklist arrived with. */
export function changedRows(
  current: TriageFormState,
  original: TriageFormState,
): TriageRowState[] {
  const before = new Map(original.rows.map((row) => [row.componentName, row]));
  return current.rows.filter((row) => {
    const was = before.get(row.componentName);
    if (!was) return row.condition !== null;
    return !rowsEqual(row, was);
  });
}

export function isDirty(
  current: TriageFormState,
  original: TriageFormState,
): boolean {
  return (
    changedRows(current, original).length > 0 ||
    current.sessionNotes.trim() !== original.sessionNotes.trim()
  );
}

/** The one client-side rule: a changed row has to say what was observed. */
export function triageFormError(
  current: TriageFormState,
  original: TriageFormState,
): string | null {
  const changed = changedRows(current, original);
  if (
    !changed.length &&
    current.sessionNotes.trim() === original.sessionNotes.trim()
  ) {
    return "Nothing has changed yet.";
  }
  const missing = changed.filter((row) => row.condition === null);
  if (missing.length) {
    return `Choose a condition for ${missing[0].componentName}.`;
  }
  return null;
}

export function toTriageRequest(
  current: TriageFormState,
  original: TriageFormState,
): AssetTriageRequest {
  const component_states = changedRows(current, original).map((row) => ({
    component_name: row.componentName,
    condition: row.condition ?? "unknown",
    repair_feasible: row.repairFeasible,
    harvest_viable: row.harvestViable,
    source_required: row.sourceRequired,
    notes: row.notes.trim() || null,
    assessed_by: current.assessedBy.trim() || null,
  }));
  return {
    component_states,
    triage_notes: current.sessionNotes.trim() || null,
  };
}

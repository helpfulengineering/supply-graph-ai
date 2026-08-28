import { describe, expect, it } from "vitest";
import type { TriageChecklist } from "@/api/ohm/asset";
import {
  changedRows,
  formStateFromChecklist,
  isDirty,
  setCondition,
  toTriageRequest,
  triageFormError,
  updateRow,
} from "./triageFormModel";

function checklist(overrides: Partial<TriageChecklist> = {}): TriageChecklist {
  return {
    asset_id: "11111111-1111-4111-8111-111111111111",
    manifest_id: "okh-0001",
    asset_tag: "OHM-0042",
    status: "active",
    last_triaged_at: null,
    items: [
      {
        component_name: "pump",
        assessed: false,
        replaceable: true,
        salvageable: false,
        consumable: false,
        part_number: "P-1",
        current_condition: null,
        current_state: null,
      },
      {
        component_name: "valve",
        assessed: true,
        replaceable: false,
        salvageable: true,
        consumable: false,
        part_number: null,
        current_condition: "damaged",
        current_state: { repair_feasible: true, notes: "seal worn" },
      },
    ],
    total_components: 2,
    assessed_count: 1,
    pending_count: 1,
    message: "1/2 components assessed",
    ...overrides,
  };
}

describe("formStateFromChecklist", () => {
  it("pre-fills recorded observations and leaves unassessed rows blank", () => {
    const state = formStateFromChecklist(checklist());
    expect(state.rows[0]).toMatchObject({
      componentName: "pump",
      condition: null,
      repairFeasible: null,
      notes: "",
    });
    expect(state.rows[1]).toMatchObject({
      componentName: "valve",
      condition: "damaged",
      repairFeasible: true,
      notes: "seal worn",
    });
  });

  it("keeps a flag the server never stated as null, not false", () => {
    // null and false are different answers to _derive_action: null means the
    // server may infer the flag from the condition, false is the technician's
    // judgement. Collapsing them changes the recommended action.
    const state = formStateFromChecklist(checklist());
    expect(state.rows[1].harvestViable).toBeNull();
    expect(state.rows[1].sourceRequired).toBeNull();
  });
});

describe("setCondition", () => {
  it("clears the flags when the new condition implies no work", () => {
    // Otherwise a row marked damaged, flagged, then corrected to intact would
    // submit repair_feasible:true about an observation that no longer exists.
    const original = formStateFromChecklist(checklist());
    const intact = setCondition(original, "valve", "intact");
    expect(intact.rows[1]).toMatchObject({
      condition: "intact",
      repairFeasible: null,
      harvestViable: null,
      sourceRequired: null,
    });
  });

  it("keeps the flags when the new condition still implies work", () => {
    const original = formStateFromChecklist(checklist());
    const missing = setCondition(original, "valve", "missing");
    expect(missing.rows[1].repairFeasible).toBe(true);
  });
});

describe("changedRows", () => {
  it("returns only the rows a technician touched", () => {
    // Triage upserts and stamps a fresh observed_at on everything it receives,
    // so an untouched row would be re-dated for an observation nobody made.
    const original = formStateFromChecklist(checklist());
    const edited = setCondition(original, "pump", "intact");
    expect(changedRows(edited, original).map((r) => r.componentName)).toEqual([
      "pump",
    ]);
  });

  it("ignores whitespace-only note edits", () => {
    const original = formStateFromChecklist(checklist());
    const edited = updateRow(original, "valve", { notes: "  seal worn  " });
    expect(changedRows(edited, original)).toEqual([]);
  });

  it("is empty when nothing changed", () => {
    const original = formStateFromChecklist(checklist());
    expect(changedRows(original, original)).toEqual([]);
    expect(isDirty(original, original)).toBe(false);
  });

  it("counts a session-note edit as dirty even with no row changes", () => {
    const original = formStateFromChecklist(checklist());
    const edited = { ...original, sessionNotes: "back panel removed" };
    expect(isDirty(edited, original)).toBe(true);
  });
});

describe("triageFormError", () => {
  it("refuses a changed row with no condition chosen", () => {
    const original = formStateFromChecklist(checklist());
    const edited = updateRow(original, "pump", { notes: "cracked housing" });
    expect(triageFormError(edited, original)).toBe(
      "Choose a condition for pump.",
    );
  });

  it("reports nothing to save when the form is untouched", () => {
    const original = formStateFromChecklist(checklist());
    expect(triageFormError(original, original)).toBe(
      "Nothing has changed yet.",
    );
  });

  it("passes once every changed row states a condition", () => {
    const original = formStateFromChecklist(checklist());
    const edited = setCondition(original, "pump", "intact");
    expect(triageFormError(edited, original)).toBeNull();
  });
});

describe("toTriageRequest", () => {
  it("submits only changed rows, carrying the session's assessor", () => {
    const original = formStateFromChecklist(checklist(), { assessedBy: "ana" });
    const edited = setCondition(original, "pump", "missing");
    const request = toTriageRequest(edited, original);
    expect(request.component_states).toEqual([
      {
        component_name: "pump",
        condition: "missing",
        repair_feasible: null,
        harvest_viable: null,
        source_required: null,
        notes: null,
        assessed_by: "ana",
      },
    ]);
  });

  it("sends session notes as null when blank rather than an empty string", () => {
    const original = formStateFromChecklist(checklist());
    const edited = setCondition(original, "pump", "intact");
    expect(toTriageRequest(edited, original).triage_notes).toBeNull();
  });
});

import { describe, expect, it } from "vitest";
import {
  ASSET_STATUSES,
  assetStatusInfo,
  assetStatusOrder,
  parseAssetStatus,
} from "./assetStatus";
import { conditionImpliesWork, conditionInfo } from "./componentCondition";
import { triageActionInfo, TRIAGE_ACTIONS } from "./triageAction";
import { assetDeleteConfirmMessage } from "./assetDeleteConfirmMessage";
import type { ComponentState } from "@/api/ohm/asset";

describe("asset statuses", () => {
  it("reads in lifecycle order", () => {
    expect(ASSET_STATUSES.map((s) => s.value)).toEqual([
      "active",
      "under_triage",
      "parts_pending",
      "under_repair",
      "restored",
      "condemned",
    ]);
  });

  it("gives every status a meaning, not just a label", () => {
    // The sentence is rendered under the control that sets the status; the
    // word alone does not say when it is the true one.
    for (const status of ASSET_STATUSES) {
      expect(status.meaning.length).toBeGreaterThan(10);
    }
  });

  it("shows an unrecognised status rather than hiding it", () => {
    // A status the app has not heard of means the backend moved; a blank badge
    // would be the frontend deciding not to mention that.
    const info = assetStatusInfo("quarantined");
    expect(info.label).toBe("quarantined");
    expect(info.tone).toBe("default");
    expect(parseAssetStatus("quarantined")).toBeNull();
  });

  it("sorts unknown statuses after every known one", () => {
    expect(assetStatusOrder("quarantined")).toBe(ASSET_STATUSES.length);
    expect(assetStatusOrder("active")).toBe(0);
  });
});

describe("component conditions", () => {
  it("asks about follow-up only where the condition implies work", () => {
    // Three tri-state controls per row is the wrong price for the common case.
    expect(conditionImpliesWork("damaged")).toBe(true);
    expect(conditionImpliesWork("missing")).toBe(true);
    expect(conditionImpliesWork("intact")).toBe(false);
    expect(conditionImpliesWork("unknown")).toBe(false);
  });

  it("falls back to a neutral display for an unknown condition", () => {
    expect(conditionInfo("charred").tone).toBe("default");
  });
});

describe("triage actions", () => {
  it("orders unassessed first and no-action last", () => {
    const ordered = [...TRIAGE_ACTIONS].sort((a, b) => a.order - b.order);
    expect(ordered[0].value).toBe("assess");
    expect(ordered[ordered.length - 1].value).toBe("no_action");
  });

  it("maps every action to a summary field that exists", () => {
    const keys = TRIAGE_ACTIONS.map((a) => a.summaryKey);
    expect(new Set(keys).size).toBe(TRIAGE_ACTIONS.length);
  });

  it("names an unknown action instead of dropping the row", () => {
    expect(triageActionInfo("scrap").label).toBe("scrap");
  });
});

describe("assetDeleteConfirmMessage", () => {
  const NOW = Date.parse("2026-08-12T12:00:00Z");
  const state = (overrides: Partial<ComponentState>): ComponentState => ({
    component_name: "pump",
    condition: "damaged",
    repair_feasible: null,
    harvest_viable: true,
    source_required: null,
    notes: null,
    observed_at: null,
    assessed_by: null,
    claimed_by: null,
    claimed_at: null,
    ...overrides,
  });

  it("is a plain question when nothing is claimed", () => {
    expect(assetDeleteConfirmMessage("OHM-0042", [state({})], NOW)).toBe(
      "Delete “OHM-0042”?",
    );
  });

  it("warns that deleting strands a live claim", () => {
    const claimed = state({
      claimed_by: "ana",
      claimed_at: new Date(NOW - 3_600_000).toISOString(),
    });
    expect(assetDeleteConfirmMessage("OHM-0042", [claimed], NOW)).toContain(
      "1 component is claimed",
    );
  });

  it("ignores a claim that has already lapsed", () => {
    const lapsed = state({
      claimed_by: "ana",
      claimed_at: new Date(NOW - 49 * 3_600_000).toISOString(),
    });
    expect(assetDeleteConfirmMessage("OHM-0042", [lapsed], NOW)).toBe(
      "Delete “OHM-0042”?",
    );
  });
});

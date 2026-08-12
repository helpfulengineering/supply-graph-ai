import { describe, expect, it } from "vitest";
import type { AssetResponse } from "@/api/ohm/asset";
import {
  buildAssetRows,
  designFilterOptions,
  groupAssetRows,
  type AssetGrouping,
} from "./assetListModel";
import { assetStatusInfo } from "./assetStatus";

function asset(overrides: Partial<AssetResponse> = {}): AssetResponse {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    manifest_id: "okh-0001",
    asset_tag: "OHM-0001",
    location: "Bay 1",
    status: "active",
    component_states: [],
    last_triaged_at: null,
    triage_notes: null,
    message: "",
    ...overrides,
  };
}

const label = (status: string) => assetStatusInfo(status).label;
const group = (assets: AssetResponse[], grouping: AssetGrouping) =>
  groupAssetRows(buildAssetRows(assets), grouping, label);

describe("buildAssetRows", () => {
  it("resolves the design title when the catalogue knows it", () => {
    const rows = buildAssetRows([asset()], {
      designTitles: new Map([["okh-0001", "Open Ventilator"]]),
    });
    expect(rows[0].designTitle).toBe("Open Ventilator");
  });

  it("falls back to the manifest id rather than showing nothing", () => {
    expect(buildAssetRows([asset()])[0].designTitle).toBe("okh-0001");
  });

  it("filters on tag, location and design title together", () => {
    const assets = [
      asset({ asset_tag: "OHM-0001", location: "Bay 1" }),
      asset({ id: "b", asset_tag: "OHM-0002", location: "Workshop" }),
    ];
    const titles = new Map([["okh-0001", "Open Ventilator"]]);
    expect(
      buildAssetRows(assets, { query: "workshop", designTitles: titles }),
    ).toHaveLength(1);
    expect(
      buildAssetRows(assets, { query: "ventilator", designTitles: titles }),
    ).toHaveLength(2);
  });
});

describe("groupAssetRows", () => {
  it("orders status groups by lifecycle, not alphabetically", () => {
    // Alphabetical opens the queue on "condemned", the one group nobody works.
    const assets = [
      asset({ id: "a", status: "condemned" }),
      asset({ id: "b", status: "active" }),
      asset({ id: "c", status: "under_repair" }),
    ];
    expect(group(assets, "status").map((g) => g.key)).toEqual([
      "active",
      "under_repair",
      "condemned",
    ]);
  });

  it("puts never-triaged units first, then the longest-neglected", () => {
    const assets = [
      asset({
        id: "a",
        asset_tag: "A",
        last_triaged_at: "2026-08-10T00:00:00Z",
      }),
      asset({ id: "b", asset_tag: "B", last_triaged_at: null }),
      asset({
        id: "c",
        asset_tag: "C",
        last_triaged_at: "2026-01-01T00:00:00Z",
      }),
    ];
    expect(group(assets, "none")[0].rows.map((r) => r.asset.asset_tag)).toEqual(
      ["B", "C", "A"],
    );
  });

  it("names the missing-location bucket and sorts it last", () => {
    const assets = [
      asset({ id: "a", location: null }),
      asset({ id: "b", location: "Bay 2" }),
    ];
    const groups = group(assets, "location");
    expect(groups.map((g) => g.label)).toEqual([
      "Bay 2",
      "No location recorded",
    ]);
  });

  it("labels design groups with the design title", () => {
    const rows = buildAssetRows([asset()], {
      designTitles: new Map([["okh-0001", "Open Ventilator"]]),
    });
    expect(groupAssetRows(rows, "design", label)[0].label).toBe(
      "Open Ventilator",
    );
  });

  it("returns one group when grouping is off", () => {
    expect(
      group([asset(), asset({ id: "b", status: "restored" })], "none"),
    ).toHaveLength(1);
  });
});

describe("designFilterOptions", () => {
  it("offers only designs the fleet actually holds, sorted by title", () => {
    const assets = [
      asset({ id: "a", manifest_id: "okh-2" }),
      asset({ id: "b", manifest_id: "okh-1" }),
      asset({ id: "c", manifest_id: "okh-1" }),
    ];
    const titles = new Map([
      ["okh-1", "Ventilator"],
      ["okh-2", "Autoclave"],
    ]);
    expect(designFilterOptions(assets, titles)).toEqual([
      { value: "okh-2", label: "Autoclave" },
      { value: "okh-1", label: "Ventilator" },
    ]);
  });
});

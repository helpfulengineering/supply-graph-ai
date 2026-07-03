import { describe, expect, it } from "vitest";
import type { OkhManifest } from "../../types/okh";
import {
  countSelected,
  deriveFacetGroups,
  filterItems,
  matchesSelections,
} from "./facets";

function item(
  id: string,
  processes: string[],
  license: string | null,
  materials: string[],
): OkhManifest {
  return {
    id,
    title: id,
    version: "1",
    repo: null,
    function: null,
    description: null,
    intended_use: null,
    keywords: [],
    documentation_language: "en",
    license: { hardware: license, documentation: null, software: null },
    licensor: { name: "x", email: null, affiliation: null, social: [] },
    contributors: [],
    manufacturing_processes: processes,
    materials: materials.map((name) => ({
      material_id: name,
      name,
      quantity: null,
      unit: "",
      notes: null,
    })),
    design_files: [],
    manufacturing_files: [],
    making_instructions: [],
    parts: [],
    tool_list: [],
    image: null,
    project_link: null,
  };
}

const items = [
  item("a", ["3D Printing", "Assembly"], "MIT", ["PLA"]),
  item("b", ["Laser Cutting"], "GPL-2.0", ["Acrylic"]),
  item("c", ["3D Printing"], "MIT", ["PLA", "Steel"]),
];

describe("faceted filtering", () => {
  it("ANDs across groups and ORs within a group", () => {
    // process ∈ {3D Printing} AND license ∈ {MIT} → a, c
    const filtered = filterItems(items, {
      process: ["3D Printing"],
      license: ["MIT"],
    });
    expect(filtered.map((i) => i.id)).toEqual(["a", "c"]);
  });

  it("OR within a group broadens", () => {
    const filtered = filterItems(items, {
      process: ["Laser Cutting", "Assembly"],
    });
    expect(filtered.map((i) => i.id).sort()).toEqual(["a", "b"]);
  });

  it("empty selections match everything", () => {
    expect(items.every((i) => matchesSelections(i, {}))).toBe(true);
  });
});

describe("deriveFacetGroups", () => {
  it("counts options and sorts by count desc", () => {
    const groups = deriveFacetGroups(items, {});
    const process = groups.find((g) => g.key === "process")!;
    expect(process.options[0]).toEqual({ value: "3D Printing", count: 2 });
    const license = groups.find((g) => g.key === "license")!;
    expect(license.options).toEqual([
      { value: "MIT", count: 2 },
      { value: "GPL-2.0", count: 1 },
    ]);
  });

  it("computes drill-down counts against other groups' selections", () => {
    // With license=GPL-2.0 selected, the process group counts only item b.
    const groups = deriveFacetGroups(items, { license: ["GPL-2.0"] });
    const process = groups.find((g) => g.key === "process")!;
    expect(process.options).toEqual([{ value: "Laser Cutting", count: 1 }]);
  });

  it("omits groups with no options (category always present via fallback)", () => {
    const groups = deriveFacetGroups([item("x", [], null, [])], {});
    // process/license/material have no values → omitted; category always yields
    // at least the Uncategorized fallback.
    expect(groups.map((g) => g.key)).toEqual(["category"]);
  });
});

describe("countSelected", () => {
  it("totals selected values across groups", () => {
    expect(countSelected({ process: ["a", "b"], license: ["MIT"] })).toBe(3);
  });
});

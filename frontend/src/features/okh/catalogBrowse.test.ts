import { describe, expect, it } from "vitest";
import type { OkhManifest } from "../../types/okh";
import { groupOkhItems, paginateGroups, sortOkhItems } from "./catalogBrowse";

function item(
  id: string,
  title: string,
  processes: string[],
  license: string | null,
  keywords: string[] = [],
): OkhManifest {
  return {
    id,
    title,
    version: "1",
    repo: null,
    function: null,
    description: null,
    intended_use: null,
    keywords,
    documentation_language: "en",
    license: { hardware: license, documentation: null, software: null },
    licensor: { name: "x", email: null, affiliation: null, social: [] },
    contributors: [],
    manufacturing_processes: processes,
    materials: [],
    design_files: [],
    manufacturing_files: [],
    making_instructions: [],
    parts: [],
    tool_list: [],
    image: null,
    project_link: null,
  };
}

describe("sortOkhItems", () => {
  it("sorts alphabetically by display title", () => {
    const items = [
      item("2", "zebra-kit", [], "MIT"),
      item("1", "alpha-board", [], "MIT"),
    ];
    expect(sortOkhItems(items, "alpha").map((i) => i.id)).toEqual(["1", "2"]);
  });

  it("sorts by category then title", () => {
    const items = [
      item("m", "zebra", [], "MIT", ["medical", "mask"]),
      item("l", "alpha", [], "MIT", ["laboratory", "lab"]),
      item("l2", "beta", [], "MIT", ["laboratory"]),
    ];
    expect(sortOkhItems(items, "category").map((i) => i.id)).toEqual([
      "l",
      "l2",
      "m",
    ]);
  });
});

describe("groupOkhItems", () => {
  it("returns a single unlabeled group when groupBy is none", () => {
    const items = [item("a", "a", [], "MIT")];
    expect(groupOkhItems(items, "none", "alpha")).toEqual([
      { label: "", items },
    ]);
  });

  it("groups by normalized license", () => {
    const items = [
      item("p", "p", [], "CERN-OHL-P-2.0"),
      item("s", "s", [], "CERN-OHL-S-2.0"),
      item("m", "m", [], "MIT"),
    ];
    const groups = groupOkhItems(items, "license", "alpha");
    expect(groups.map((g) => g.label)).toEqual(["CERN-OHL-2.0", "MIT"]);
    expect(groups[0].items.map((i) => i.id).sort()).toEqual(["p", "s"]);
  });
});

describe("paginateGroups", () => {
  it("slices across groups and rebuilds headers", () => {
    const groups = groupOkhItems(
      [
        item("a", "a", [], "MIT"),
        item("b", "b", [], "MIT"),
        item("c", "c", [], "MIT"),
        item("d", "d", [], "MIT"),
      ],
      "license",
      "alpha",
    );
    const page1 = paginateGroups(groups, 1, 2);
    expect(page1).toHaveLength(1);
    expect(page1[0].items.map((i) => i.id)).toEqual(["a", "b"]);
    const page2 = paginateGroups(groups, 2, 2);
    expect(page2[0].items.map((i) => i.id)).toEqual(["c", "d"]);
  });
});

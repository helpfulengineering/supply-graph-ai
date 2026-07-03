import { describe, expect, it } from "vitest";
import type { OkhManifest } from "../../types/okh";
import { deriveCategories, UNCATEGORIZED } from "./categories";

function withFunction(fn: string, title = "x"): OkhManifest {
  return {
    id: "x",
    title,
    version: null,
    repo: null,
    function: fn,
    description: null,
    intended_use: null,
    keywords: [],
    documentation_language: null,
    license: null,
    licensor: null,
    contributors: [],
    manufacturing_processes: [],
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

describe("deriveCategories", () => {
  it("derives a category from the function text", () => {
    expect(deriveCategories(withFunction("A laboratory centrifuge"))).toContain(
      "Laboratory & Bio",
    );
  });

  it("is multi-valued — a device can belong to several categories", () => {
    const cats = deriveCategories(
      withFunction("A laboratory centrifuge driven by a peristaltic pump"),
    );
    expect(cats).toContain("Laboratory & Bio");
    expect(cats).toContain("Fluid Handling");
    expect(cats.length).toBeGreaterThan(1);
  });

  it("matches on title and keywords too", () => {
    const item = withFunction("Does things", "Emergency Ventilator");
    expect(deriveCategories(item)).toContain("Medical & PPE");
  });

  it("falls back to Uncategorized when nothing matches", () => {
    expect(deriveCategories(withFunction("An inscrutable widget"))).toEqual([
      UNCATEGORIZED,
    ]);
  });
});

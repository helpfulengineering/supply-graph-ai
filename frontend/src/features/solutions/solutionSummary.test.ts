import { describe, expect, it } from "vitest";
import { formatSaved, scorePercent, solutionLabel } from "./solutionSummary";
import type { SolutionSummary } from "../../api/ohm/supply-tree";

function fixture(overrides: Partial<SolutionSummary> = {}): SolutionSummary {
  return {
    id: "sol-1",
    okh_id: "okh-0001",
    okh_title: "Foldable Solar Dryer",
    facility_name: "FabLab Drome",
    matching_mode: "single-level",
    tree_count: 1,
    facility_count: 1,
    score: 0.95,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("solutionLabel", () => {
  it("prefers the design title", () => {
    expect(solutionLabel(fixture())).toBe("Foldable Solar Dryer");
  });

  /**
   * A match run against a pasted or generated manifest saves a solution with
   * no title, because the design was never in the catalogue to have one. The
   * row still has to name itself.
   */
  it("falls back to a short id when the design has no title", () => {
    expect(solutionLabel(fixture({ okh_title: null }))).toBe("okh-0001…");
  });

  it("names the untitled case rather than rendering an empty card", () => {
    expect(solutionLabel(fixture({ okh_title: null, okh_id: null }))).toBe(
      "Untitled solution",
    );
  });
});

describe("scorePercent", () => {
  it("renders a fraction as whole percent", () => {
    expect(scorePercent(0.95)).toBe(95);
    expect(scorePercent(0)).toBe(0);
  });

  /**
   * Returns null rather than 0 so the caller can drop the badge entirely. A
   * missing score rendered as "0%" reads as a scored-and-failed match, which
   * is a different claim from "not scored".
   */
  it("distinguishes absent from zero", () => {
    expect(scorePercent(null)).toBeNull();
    expect(scorePercent(undefined)).toBeNull();
    expect(scorePercent(Number.NaN)).toBeNull();
  });
});

describe("formatSaved", () => {
  it("formats a timestamp", () => {
    expect(formatSaved("2026-01-01T00:00:00Z")).not.toBe("");
  });

  it("returns empty for absent or unparseable input, never Invalid Date", () => {
    expect(formatSaved(null)).toBe("");
    expect(formatSaved("not a date")).toBe("");
  });
});

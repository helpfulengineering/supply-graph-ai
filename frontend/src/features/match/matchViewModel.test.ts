import { describe, expect, it } from "vitest";
import { toMatchView } from "./matchViewModel";

const raw = {
  data: {
    solutions: [
      { facility_name: "B", facility_id: "b", confidence: 0.7, score: 0.7, rank: 2, explanation_human: "ok", tree: { id: "t-b" } },
      { facility_name: "A", facility_id: "a", confidence: 0.95, score: 0.95, rank: 1, explanation_human: "great", tree: { id: "t-a" } },
      { facility_name: "C", facility_id: "c", confidence: 0.95, score: 0.9, rank: 3 },
    ],
    coverage_gaps: ["CNC Machining"],
    human_summary: { executive: "3 candidate solutions found." },
    total_solutions: 3,
    solution_id: "sol-123",
  },
};

describe("toMatchView", () => {
  it("sorts by confidence desc, then rank asc", () => {
    const view = toMatchView(raw);
    expect(view.solutions.map((s) => s.facilityName)).toEqual(["A", "C", "B"]);
  });

  it("extracts summary, coverage gaps, and total", () => {
    const view = toMatchView(raw);
    expect(view.summary).toBe("3 candidate solutions found.");
    expect(view.coverageGaps).toEqual(["CNC Machining"]);
    expect(view.totalSolutions).toBe(3);
  });

  it("surfaces the persisted solution id for hand-off", () => {
    expect(toMatchView(raw).solutionId).toBe("sol-123");
    expect(toMatchView({ data: { solutions: [] } }).solutionId).toBeNull();
  });

  it("handles an empty/no-match response", () => {
    expect(toMatchView({}).solutions).toEqual([]);
    expect(toMatchView({ data: { solutions: [] } }).totalSolutions).toBe(0);
  });
});

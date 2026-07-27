import { describe, expect, it } from "vitest";
import { solutionSelectionKey, toMatchView } from "./matchViewModel";
import { toRfqSolutions } from "./rfqHandoff";

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

  it("surfaces per-solution tree ids and the persisted solution id", () => {
    const view = toMatchView(raw);
    expect(view.solutions.map((s) => s.treeId)).toEqual(["t-a", null, "t-b"]);
    expect(view.solutionId).toBe("sol-123");
    expect(toMatchView({ data: { solutions: [] } }).solutionId).toBeNull();
  });

  it("handles an empty/no-match response", () => {
    expect(toMatchView({}).solutions).toEqual([]);
    expect(toMatchView({ data: { solutions: [] } }).totalSolutions).toBe(0);
  });
});

describe("solutionSelectionKey", () => {
  it("prefers facility id then tree id", () => {
    const view = toMatchView(raw);
    expect(solutionSelectionKey(view.solutions[0], 0)).toBe("a");
    expect(solutionSelectionKey(view.solutions[2], 2)).toBe("b");
  });
});

describe("toRfqSolutions", () => {
  it("maps ranked solutions into RFQ navigation payloads", () => {
    const view = toMatchView(raw);
    const rfq = toRfqSolutions([view.solutions[0]], { a: "https://example.org" });
    expect(rfq).toHaveLength(1);
    expect(rfq[0].facility_id).toBe("a");
    expect(rfq[0].tree.id).toBe("t-a");
    expect(rfq[0].facility.contact?.website).toBe("https://example.org");
  });
});

// The card showed "confidence 100%" beside text reading "(confidence: 95%)".
// They are different fields: `confidence` is coverage-derived and reads 1.0
// whenever every requirement matched, while `overall_confidence` is the mean of
// the per-requirement confidences the text quotes.
describe("confidence is a single, evidenced figure", () => {
  const raw = (solution: Record<string, unknown>) => ({
    data: { solutions: [solution] },
  });

  it("prefers the explanation's overall confidence", () => {
    const view = toMatchView(
      raw({
        facility_name: "FabLab",
        confidence: 1.0,
        explanation: { overall_confidence: 0.95, requirement_matches: [] },
      }),
    );
    expect(view.solutions[0].confidence).toBe(0.95);
  });

  it("falls back to the solution confidence when the explanation omits it", () => {
    const view = toMatchView(raw({ facility_name: "FabLab", confidence: 0.8 }));
    expect(view.solutions[0].confidence).toBe(0.8);
  });

  it("defaults to zero rather than undefined", () => {
    const view = toMatchView(raw({ facility_name: "FabLab" }));
    expect(view.solutions[0].confidence).toBe(0);
  });
});

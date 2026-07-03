import { describe, expect, it } from "vitest";
import type { VisualizationData } from "../../types/supply-tree";
import {
  deriveKpis,
  isSolutionEmpty,
  toDependencies,
  toProductionSequence,
} from "./supplyTreeAdapter";

function bundle(over: Partial<VisualizationData> = {}): VisualizationData {
  return {
    schema_version: "3.2.0",
    source_type: "solution",
    generated_at: "now",
    matching: { overview: { matching_mode: "single-level", score: 1, tree_count: 1 } },
    supply_tree: {
      solution_id: "s1",
      nodes: [{ id: "n1" } as never],
      edges: [],
      dependency_graph: {},
      production_sequence: [],
      resource_cost: { total_estimated_cost: null, total_estimated_time: null },
    },
    network: { facility_distribution: [], route_hints: { status: "x", note: "" } },
    dashboard: { kpis: { tree_count: 2, edge_count: 3, stage_count: 4, solution_score: 0.9 } },
    artifacts: {},
    ...over,
  } as VisualizationData;
}

describe("supplyTreeAdapter", () => {
  it("derives KPIs from the dashboard block", () => {
    const kpis = deriveKpis(bundle());
    expect(kpis).toEqual(
      expect.arrayContaining([
        { label: "Trees", value: "2" },
        { label: "Dependencies", value: "3" },
        { label: "Stages", value: "4" },
        { label: "Score", value: "90%" },
      ]),
    );
  });

  it("adds cost/time KPIs only when present", () => {
    const withCost = bundle({
      supply_tree: {
        ...bundle().supply_tree,
        resource_cost: { total_estimated_cost: 42, total_estimated_time: 7 },
      },
    });
    const labels = deriveKpis(withCost).map((k) => k.label);
    expect(labels).toContain("Est. cost");
    expect(labels).toContain("Est. time");
    expect(deriveKpis(bundle()).map((k) => k.label)).not.toContain("Est. cost");
  });

  it("detects an empty solution (no nodes)", () => {
    expect(isSolutionEmpty(bundle())).toBe(false);
    const empty = bundle({ supply_tree: { ...bundle().supply_tree, nodes: [] } });
    expect(isSolutionEmpty(empty)).toBe(true);
  });

  const seqBundle = bundle({
    supply_tree: {
      ...bundle().supply_tree,
      nodes: [{ id: "n1", label: "Frame" } as never, { id: "n2", label: "Base" } as never],
      production_sequence: [["n2"], ["n1"]],
      dependency_graph: { n1: ["n2"] },
    },
  });

  it("labels production-sequence stages in order", () => {
    expect(toProductionSequence(seqBundle)).toEqual([
      { index: 1, items: ["Base"] },
      { index: 2, items: ["Frame"] },
    ]);
  });

  it("labels dependencies and skips nodes with none", () => {
    expect(toDependencies(seqBundle)).toEqual([{ node: "Frame", dependsOn: ["Base"] }]);
  });

  it("returns empty sequence/deps for a bare solution", () => {
    expect(toProductionSequence(bundle())).toEqual([]);
    expect(toDependencies(bundle())).toEqual([]);
  });
});

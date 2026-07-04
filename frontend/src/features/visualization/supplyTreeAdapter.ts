import type { VisualizationData } from "../../types/supply-tree";

/**
 * Supply-tree adapter (pure, unit-tested) — module 3.
 * Derives presentation-ready KPIs from the visualization bundle and detects an
 * empty solution. The cytoscape graph + echarts chart consume the bundle
 * directly; this owns the derived summary logic.
 */

export interface Kpi {
  label: string;
  value: string;
}

export function isSolutionEmpty(bundle: VisualizationData): boolean {
  return (bundle.supply_tree?.nodes?.length ?? 0) === 0;
}

function labelLookup(bundle: VisualizationData): Map<string, string> {
  return new Map(
    (bundle.supply_tree?.nodes ?? []).map((n) => [n.id, n.label || n.facility_name || n.id]),
  );
}

export interface SequenceStage {
  index: number;
  items: string[];
}

/** Production sequence as ordered stages of readable node labels. */
export function toProductionSequence(bundle: VisualizationData): SequenceStage[] {
  const byId = labelLookup(bundle);
  return (bundle.supply_tree?.production_sequence ?? []).map((stage, i) => ({
    index: i + 1,
    items: stage.map((id) => byId.get(id) ?? id),
  }));
}

export interface NodeDependencies {
  node: string;
  dependsOn: string[];
}

/** Per-node dependency list (only nodes that depend on something), labelled. */
export function toDependencies(bundle: VisualizationData): NodeDependencies[] {
  const byId = labelLookup(bundle);
  return Object.entries(bundle.supply_tree?.dependency_graph ?? {})
    .filter(([, deps]) => (deps?.length ?? 0) > 0)
    .map(([id, deps]) => ({
      node: byId.get(id) ?? id,
      dependsOn: deps.map((d) => byId.get(d) ?? d),
    }));
}

export function deriveKpis(bundle: VisualizationData): Kpi[] {
  const kpis = bundle.dashboard?.kpis;
  const cost = bundle.supply_tree?.resource_cost;
  const out: Kpi[] = [
    { label: "Trees", value: String(kpis?.tree_count ?? 0) },
    { label: "Stages", value: String(kpis?.stage_count ?? 0) },
    { label: "Dependencies", value: String(kpis?.edge_count ?? 0) },
    { label: "Score", value: `${Math.round((kpis?.solution_score ?? 0) * 100)}%` },
  ];
  if (cost?.total_estimated_cost != null) {
    out.push({ label: "Est. cost", value: String(cost.total_estimated_cost) });
  }
  if (cost?.total_estimated_time != null) {
    out.push({ label: "Est. time", value: String(cost.total_estimated_time) });
  }
  return out;
}

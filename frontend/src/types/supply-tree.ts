/** Supply tree / visualization types derived from fixture contract (schema 3.2.0). */

export interface VisualizationNode {
  id: string;
  label: string;
  component_id: string | null;
  facility_name: string;
  depth: number;
  production_stage: string;
  confidence_score: number;
  estimated_cost: number | null;
  estimated_time: number | null;
}

export interface VisualizationEdge {
  source: string;
  target: string;
  type: string;
}

export interface SupplyTree {
  solution_id: string;
  nodes: VisualizationNode[];
  edges: VisualizationEdge[];
  dependency_graph: Record<string, string[]>;
  production_sequence: string[][];
  resource_cost: {
    total_estimated_cost: number | null;
    total_estimated_time: number | null;
  };
}

export interface VisualizationData {
  schema_version: string;
  source_type: string;
  generated_at: string;
  matching: {
    overview: {
      matching_mode: string;
      score: number;
      tree_count: number;
    };
  };
  supply_tree: SupplyTree;
  network: {
    facility_distribution: { facility_name: string; tree_count: number }[];
    route_hints: { status: string; note: string };
  };
  dashboard: {
    kpis: {
      tree_count: number;
      edge_count: number;
      stage_count: number;
      solution_score: number;
    };
  };
  artifacts: {
    graphml_endpoint?: string;
    json_bundle?: boolean | string;
    html_report?: boolean | string;
  };
}

export interface VisualizationResponse {
  status: string;
  message: string;
  timestamp: string;
  request_id: string;
  data: VisualizationData;
  metadata: Record<string, unknown>;
}

export interface SolutionSummary {
  id: string;
  okh_id: string;
  okh_title: string | null;
  matching_mode: string;
  total_trees: number;
  total_components: number;
  total_facilities: number;
  average_confidence: number;
  score: number;
  is_nested: boolean;
  cost_estimate: number | null;
  time_estimate: number | null;
  facility_distribution: { facility_name: string; count: number }[];
}

export interface SolutionListItem {
  id: string;
  okh_id: string;
  okh_title: string | null;
  matching_mode: string;
  tree_count: number;
  component_count: number;
  facility_count: number;
  score: number;
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  ttl_days: number | null;
  tags: string[];
  age_days: number | null;
}

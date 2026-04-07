/** Match request/response types derived from fixture contract. */

export interface MatchRequest {
  okh_id: string;
  max_results?: number;
  save_solution?: boolean;
  solution_tags?: string[];
  solution_ttl_days?: number;
  include_human_summary?: boolean;
  include_explanation?: boolean;
}

export interface FacilityLocation {
  city: string;
  country: string;
  gps_coordinates?: string;
}

export interface FacilityContact {
  name?: string;
  contact_person?: string;
  website?: string;
  languages?: string[];
}

export interface FacilityEquipment {
  equipment_type: string;
  manufacturing_process: string;
  make?: string;
  model?: string;
  condition?: string;
  quantity?: number;
}

export interface Facility {
  id: string;
  name: string;
  location: FacilityLocation;
  facility_status?: string;
  description?: string;
  access_type?: string;
  manufacturing_processes: string[];
  certifications?: string[];
  equipment?: FacilityEquipment[];
  contact?: FacilityContact;
  typical_batch_size?: string;
  date_founded?: string;
}

export interface RequirementMatch {
  requirement_value: string;
  status: "matched" | "not_matched";
  confidence: number;
  matched_capability: string | null;
  matching_layer: string | null;
  explanation: string;
  requirement_source: string;
  requirement_part_name?: string;
}

export interface MatchExplanation {
  facility_id: string;
  facility_name: string;
  overall_status: "matched" | "not_matched";
  overall_confidence: number;
  requirement_matches: RequirementMatch[];
  why_matched: string;
  why_not_matched: string;
  matching_layers_used: string[];
  missing_capabilities: string[];
}

export interface SolutionTree {
  id: string;
  facility_name: string;
  okh_reference: string;
  confidence_score: number;
  estimated_cost: number | null;
  estimated_time: number | null;
  match_type: string;
  depth: number;
  production_stage: string;
  metadata: Record<string, unknown>;
}

export interface MatchSolution {
  tree: SolutionTree;
  facility: Facility;
  facility_id: string;
  facility_name: string;
  match_type: string;
  confidence: number;
  score: number;
  rank: number;
  metrics: { facility_count: number; requirement_count: number; capability_count: number };
  explanation: MatchExplanation | null;
  explanation_human: string | null;
}

export interface HumanSummaryInsights {
  risks: string[];
  opportunities: string[];
  recommendations: string[];
}

export interface HumanSummary {
  profile: string;
  executive: string;
  technical: string;
  detailed: string[];
  key_insights: HumanSummaryInsights;
}

export interface MatchResponseData {
  solutions: MatchSolution[];
  total_solutions: number;
  matching_mode: string;
  processing_time: number;
  match_summary_text: string;
  coverage_gaps: string[];
  suggestions: string[];
  suggestion_codes: string[];
  human_summary?: HumanSummary;
  solution_id?: string;
}

export interface MatchResponse {
  status: string;
  message: string;
  timestamp: string;
  request_id: string;
  data: MatchResponseData;
  metadata: Record<string, unknown>;
}

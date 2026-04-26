/** RFQ generation request / response types. */

import type { MatchSolution } from "./match";

export interface RFQSolutionInput {
  facility_id: string;
  facility_name: string;
  confidence: number;
  score: number;
  rank: number;
  tree: Record<string, unknown>;
  facility: Record<string, unknown>;
}

export interface RFQGenerateRequest {
  okh_id: string;
  okh_title: string;
  okh_function?: string;
  okh_version?: string;
  quantity: number;
  solutions: RFQSolutionInput[];
  /** Full OKH manifest — embedded in the generated document and JSON export. */
  okh_manifest?: Record<string, unknown>;
}

export interface RFQDocument {
  rfq_number: string;
  facility_name: string;
  facility_id: string;
  confidence: number;
  rank: number;
  quantity: number;
  text: string;
  okh_manifest?: Record<string, unknown>;
}

export interface RFQGenerateResponseData {
  rfqs: RFQDocument[];
  total_rfqs: number;
  okh_id: string;
  okh_title: string;
  generated_at: string;
}

export interface RFQGenerateResponse {
  status: string;
  message: string;
  timestamp: string;
  data: RFQGenerateResponseData;
}

/** State passed via react-router when navigating to the RFQ page. */
export interface RfqNavigationState {
  okhId: string;
  okhTitle: string;
  okhFunction?: string;
  okhVersion?: string;
  solutions: MatchSolution[];
}

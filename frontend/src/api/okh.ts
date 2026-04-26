import { get } from "./client";
import type { OkhListResponse, OkhManifest } from "../types/okh";

export interface OkhListParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export function fetchOkhList(params: OkhListParams = {}): Promise<OkhListResponse> {
  return get<OkhListResponse>("/okh", {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
    sort_by: params.sort_by,
    sort_order: params.sort_order,
  });
}

export interface OkhDetailResponse {
  status: string;
  message: string;
  data: null;
  // OKH manifest fields are at the top level (not nested under data)
  id: string;
  title: string;
  [key: string]: unknown;
}

export function fetchOkhDetail(id: string): Promise<OkhManifest> {
  // The OKH detail endpoint returns manifest fields at the top level (not
  // under data). Cast the response through unknown to satisfy TypeScript.
  return get<OkhManifest>(`/okh/${id}`);
}

import { apiClient, ApiError, errorMessage } from "./client";
import type { OkwFacility } from "../../types/okw";

export interface OkwSearchResult {
  results: OkwFacility[];
  total: number;
  page: number;
  page_size: number;
}

export interface SearchOkwParams {
  page?: number;
  page_size?: number;
  location?: string;
  access_type?: string;
  facility_status?: string;
}

/**
 * Search OKW facilities. Response envelope is `{results, total, page, page_size}`
 * (distinct from OKH's `{items, pagination}`); results are narrowed to the
 * OkwFacility view type the catalog renders.
 */
export async function searchOkw(
  params: SearchOkwParams = {},
): Promise<OkwSearchResult> {
  const { data, error, response } = await apiClient.GET("/api/okw/search", {
    params: {
      query: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 100,
        location: params.location,
        access_type: params.access_type,
        facility_status: params.facility_status,
      },
    },
  });

  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load facilities (HTTP ${response.status})`),
    );
  }

  const body = (data ?? {}) as {
    results?: unknown[];
    total?: number;
    page?: number;
    page_size?: number;
  };
  return {
    results: (body.results ?? []) as OkwFacility[],
    total: body.total ?? 0,
    page: body.page ?? 1,
    page_size: body.page_size ?? 0,
  };
}

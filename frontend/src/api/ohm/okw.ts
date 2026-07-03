import { apiClient, ApiError, errorMessage } from "./client";
import type { OkwFacility } from "../../types/okw";
import type { components } from "../generated/schema";

export type ValidationResult = components["schemas"]["ValidationResult"];

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

/** Fetch a single OKW facility by id (fields returned at the top level). */
export async function fetchOkwDetail(id: string): Promise<OkwFacility> {
  const { data, error, response } = await apiClient.GET("/api/okw/{id}", {
    params: { path: { id } },
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load facility (HTTP ${response.status})`),
    );
  }
  return data as unknown as OkwFacility;
}

/** Validate an OKW facility against domain rules; returns the validation result. */
export async function validateOkw(
  content: Record<string, unknown>,
): Promise<ValidationResult> {
  const { data, error, response } = await apiClient.POST("/api/okw/validate", {
    body: { content },
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Validation failed (HTTP ${response.status})`),
    );
  }
  return data as ValidationResult;
}

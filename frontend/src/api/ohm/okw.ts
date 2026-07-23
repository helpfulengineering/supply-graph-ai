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

export type RecordProvenance = components["schemas"]["RecordProvenance"];
export type VisibilityLevel = components["schemas"]["VisibilityLevel"];
export type VisibilityResponse = components["schemas"]["VisibilityResponse"];

export interface CreateProvenanceOpts {
  author?: string;
  onBehalfOf?: string;
}

/** Create and store an OKW facility from JSON (requires write). */
export async function createOkw(
  content: Record<string, unknown>,
  opts: CreateProvenanceOpts = {},
): Promise<{ id: string }> {
  const { data, error, response } = await apiClient.POST("/api/okw/create", {
    params: {
      query: { author: opts.author, on_behalf_of: opts.onBehalfOf },
    },
    body: { content },
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to create facility (HTTP ${response.status})`),
    );
  }
  const id = data.okw?.id;
  if (!id) {
    throw new ApiError(response.status, "Create succeeded but response had no id");
  }
  return { id: String(id) };
}

export async function getOkwProvenance(id: string): Promise<RecordProvenance | null> {
  const { data, error, response } = await apiClient.GET("/api/okw/{id}/provenance", {
    params: { path: { id } },
  });
  if (response.status === 404) return null;
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load provenance (HTTP ${response.status})`),
    );
  }
  return data;
}

export async function getOkwVisibility(id: string): Promise<VisibilityResponse> {
  const { data, error, response } = await apiClient.GET("/api/okw/{id}/visibility", {
    params: { path: { id } },
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load visibility (HTTP ${response.status})`),
    );
  }
  return data;
}

export async function setOkwVisibility(
  id: string,
  visibility: VisibilityLevel,
): Promise<VisibilityResponse> {
  const { data, error, response } = await apiClient.PUT("/api/okw/{id}/visibility", {
    params: { path: { id } },
    body: { visibility },
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to set visibility (HTTP ${response.status})`),
    );
  }
  return data;
}

export type DisclosureGroup = components["schemas"]["DisclosureGroup"];
export type DisclosureAudience = components["schemas"]["DisclosureAudience"];
export type AudienceDisclosure = components["schemas"]["AudienceDisclosure"];
export type DisclosureProfile = components["schemas"]["DisclosureProfile"];
export type DisclosureResponse = components["schemas"]["DisclosureResponse"];
export type DisclosurePreviewResponse =
  components["schemas"]["DisclosurePreviewResponse"];

export async function getOkwDisclosure(id: string): Promise<DisclosureResponse> {
  const { data, error, response } = await apiClient.GET("/api/okw/{id}/disclosure", {
    params: { path: { id } },
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load disclosure (HTTP ${response.status})`),
    );
  }
  return data;
}

export async function setOkwDisclosure(
  id: string,
  body: Partial<DisclosureProfile>,
): Promise<DisclosureResponse> {
  const { data, error, response } = await apiClient.PUT("/api/okw/{id}/disclosure", {
    params: { path: { id } },
    body,
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to set disclosure (HTTP ${response.status})`),
    );
  }
  return data;
}

export async function previewOkwDisclosure(
  id: string,
  audience: DisclosureAudience = "followers",
): Promise<DisclosurePreviewResponse> {
  const { data, error, response } = await apiClient.GET(
    "/api/okw/{id}/disclosure/preview",
    { params: { path: { id }, query: { audience } } },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to preview disclosure (HTTP ${response.status})`),
    );
  }
  return data;
}

/** Update an OKW facility (requires write). */
export async function updateOkw(
  id: string,
  body: components["schemas"]["OKWUpdateRequest"],
): Promise<OkwFacility> {
  const { data, error, response } = await apiClient.PUT("/api/okw/{id}", {
    params: { path: { id } },
    body,
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to update facility (HTTP ${response.status})`),
    );
  }
  return data as unknown as OkwFacility;
}

/** Delete an OKW facility (requires write). */
export async function deleteOkw(id: string): Promise<void> {
  const { error, response } = await apiClient.DELETE("/api/okw/{id}", {
    params: { path: { id } },
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to delete facility (HTTP ${response.status})`),
    );
  }
}

import { apiClient, ApiError, errorMessage } from "./client";
import type { OkhManifest } from "../../types/okh";
import type { components } from "../generated/schema";

export type ValidationResult = components["schemas"]["ValidationResult"];

export interface OkhPagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface OkhListResult {
  items: OkhManifest[];
  pagination: OkhPagination;
}

export interface FetchOkhListParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  filter?: string;
}

const EMPTY_PAGINATION: OkhPagination = {
  page: 1,
  page_size: 0,
  total_items: 0,
  total_pages: 1,
  has_next: false,
  has_previous: false,
};

/**
 * List OKH design manifests. The backend types the list response as a generic
 * paginated envelope (items: object[]), so we narrow items to the OkhManifest
 * view type the UI renders.
 */
export async function fetchOkhList(
  params: FetchOkhListParams = {},
): Promise<OkhListResult> {
  const { data, error, response } = await apiClient.GET("/api/okh", {
    params: {
      query: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 100,
        sort_by: params.sort_by,
        sort_order: params.sort_order,
        filter: params.filter,
      },
    },
  });

  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load designs (HTTP ${response.status})`),
    );
  }

  const body = (data ?? {}) as {
    items?: unknown[];
    pagination?: Partial<OkhPagination>;
  };
  return {
    items: (body.items ?? []) as OkhManifest[],
    pagination: { ...EMPTY_PAGINATION, ...body.pagination },
  };
}

const CATALOG_PAGE_SIZE = 100;
/** Safety cap so a buggy has_next never loops forever. */
const CATALOG_MAX_PAGES = 50;

/**
 * Fetch every OKH list page and merge into one result (deduped by id).
 * Used by catalog/match UIs that need the full set for client-side facets.
 */
export async function fetchAllOkhList(
  params: Omit<FetchOkhListParams, "page" | "page_size"> = {},
): Promise<OkhListResult> {
  const byId = new Map<string, OkhManifest>();
  let page = 1;
  let lastPagination = EMPTY_PAGINATION;

  while (page <= CATALOG_MAX_PAGES) {
    const result = await fetchOkhList({
      ...params,
      page,
      page_size: CATALOG_PAGE_SIZE,
    });
    lastPagination = result.pagination;
    for (const item of result.items) {
      if (item?.id != null && !byId.has(item.id)) {
        byId.set(item.id, item);
      }
    }
    const total = result.pagination.total_items ?? 0;
    const hasNext = result.pagination.has_next === true;
    if (!hasNext || byId.size >= total || result.items.length === 0) {
      break;
    }
    page += 1;
  }

  const items = Array.from(byId.values());
  return {
    items,
    pagination: {
      ...lastPagination,
      page: 1,
      page_size: items.length,
      total_items: lastPagination.total_items || items.length,
      total_pages: 1,
      has_next: false,
      has_previous: false,
    },
  };
}

/** Fetch a single OKH manifest by id (fields returned at the top level). */
export async function fetchOkhDetail(id: string): Promise<OkhManifest> {
  const { data, error, response } = await apiClient.GET("/api/okh/{id}", {
    params: { path: { id } },
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load design (HTTP ${response.status})`),
    );
  }
  return data as unknown as OkhManifest;
}

export interface ValidateOkhOptions {
  qualityLevel?: string;
  strictMode?: boolean;
}

/** Validate an OKH manifest against domain rules; returns the validation result. */
export async function validateOkh(
  content: Record<string, unknown>,
  opts: ValidateOkhOptions = {},
): Promise<ValidationResult> {
  const { data, error, response } = await apiClient.POST("/api/okh/validate", {
    params: {
      query: { quality_level: opts.qualityLevel, strict_mode: opts.strictMode },
    },
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

/** Create and store an OKH manifest from JSON (requires write). */
export async function createOkh(
  content: Record<string, unknown>,
  opts: CreateProvenanceOpts = {},
): Promise<{ id: string }> {
  const { data, error, response } = await apiClient.POST("/api/okh/create", {
    params: {
      query: { author: opts.author, on_behalf_of: opts.onBehalfOf },
    },
    body: { content },
  });
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to create design (HTTP ${response.status})`),
    );
  }
  const id = data.okh?.id;
  if (!id) {
    throw new ApiError(response.status, "Create succeeded but response had no id");
  }
  return { id: String(id) };
}

export async function getOkhProvenance(id: string): Promise<RecordProvenance | null> {
  const { data, error, response } = await apiClient.GET("/api/okh/{id}/provenance", {
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

export async function getOkhVisibility(id: string): Promise<VisibilityResponse> {
  const { data, error, response } = await apiClient.GET("/api/okh/{id}/visibility", {
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

export async function setOkhVisibility(
  id: string,
  visibility: VisibilityLevel,
): Promise<VisibilityResponse> {
  const { data, error, response } = await apiClient.PUT("/api/okh/{id}/visibility", {
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

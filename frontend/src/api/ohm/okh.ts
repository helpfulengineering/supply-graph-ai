import { apiClient, ApiError, errorMessage } from "./client";
import type { OkhManifest } from "../../types/okh";

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

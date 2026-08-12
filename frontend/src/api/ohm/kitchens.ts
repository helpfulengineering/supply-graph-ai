import { apiClient, ApiError, errorMessage } from "./client";
import type { Kitchen } from "../../types/kitchen";

/** List-only: kitchens are uploaded to storage directly, not created via the UI. */
export async function fetchAllKitchens(): Promise<Kitchen[]> {
  const byId = new Map<string, Kitchen>();
  let page = 1;
  const pageSize = 100;

  while (true) {
    const { data, error, response } = await apiClient.GET("/api/okw/kitchens", {
      params: { query: { page, page_size: pageSize } },
    });
    if (error || !response.ok) {
      throw new ApiError(
        response.status,
        errorMessage(error, `Failed to load kitchens (HTTP ${response.status})`),
      );
    }

    const body = (data ?? {}) as {
      items?: Kitchen[];
      pagination?: { has_next?: boolean; total_items?: number };
    };
    for (const kitchen of body.items ?? []) {
      if (kitchen?.id != null) byId.set(kitchen.id, kitchen);
    }

    const total = body.pagination?.total_items ?? 0;
    const hasNext = body.pagination?.has_next === true;
    if (!hasNext || byId.size >= total || (body.items ?? []).length === 0) break;
    page += 1;
  }

  return Array.from(byId.values());
}

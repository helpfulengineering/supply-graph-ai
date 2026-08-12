import { apiClient, ApiError, errorMessage } from "./client";
import type { Recipe } from "../../types/recipe";

/** List-only: recipes are uploaded to storage directly, not created via the UI. */
export async function fetchAllRecipes(): Promise<Recipe[]> {
  const byId = new Map<string, Recipe>();
  let page = 1;
  const pageSize = 100;

  while (true) {
    const { data, error, response } = await apiClient.GET("/api/okh/recipes", {
      params: { query: { page, page_size: pageSize } },
    });
    if (error || !response.ok) {
      throw new ApiError(
        response.status,
        errorMessage(error, `Failed to load recipes (HTTP ${response.status})`),
      );
    }

    const body = (data ?? {}) as {
      items?: Recipe[];
      pagination?: { has_next?: boolean; total_items?: number };
    };
    for (const recipe of body.items ?? []) {
      if (recipe?.id != null) byId.set(recipe.id, recipe);
    }

    const total = body.pagination?.total_items ?? 0;
    const hasNext = body.pagination?.has_next === true;
    if (!hasNext || byId.size >= total || (body.items ?? []).length === 0) break;
    page += 1;
  }

  return Array.from(byId.values());
}

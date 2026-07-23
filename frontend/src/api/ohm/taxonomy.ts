import { apiClient, ApiError, errorMessage } from "./client";
import type { TaxonomyProcess } from "../../features/okw/facilityFormModel";

type RawProcess = {
  canonical_id?: string;
  display_name?: string;
  parent?: string | null;
  children?: string[];
};

/** Load process taxonomy (processes.yaml via GET /api/taxonomy). */
export async function fetchProcessTaxonomy(): Promise<TaxonomyProcess[]> {
  const { data, error, response } = await apiClient.GET("/api/taxonomy");
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load taxonomy (HTTP ${response.status})`),
    );
  }
  const raw =
    ((data as { data?: { processes?: RawProcess[] } } | null)?.data?.processes) ??
    [];
  return raw
    .filter((p): p is RawProcess & { canonical_id: string } =>
      Boolean(p.canonical_id),
    )
    .map((p) => ({
      canonical_id: p.canonical_id,
      display_name: p.display_name || p.canonical_id,
      parent: p.parent ?? null,
      children: Array.isArray(p.children) ? p.children : [],
    }));
}

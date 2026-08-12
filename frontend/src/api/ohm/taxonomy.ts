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
    (data as { data?: { processes?: RawProcess[] } } | null)?.data?.processes ??
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

export interface TaxonomyValidation {
  valid: boolean;
  total_processes: number;
  errors: string[];
  source: string;
}

/** Check processes.yaml on the server's disk, without applying it. */
export async function validateProcessTaxonomy(): Promise<TaxonomyValidation> {
  const { data, error, response } = await apiClient.GET(
    "/api/taxonomy/validate",
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Validation failed (HTTP ${response.status})`),
    );
  }
  const body =
    (data as { data?: Partial<TaxonomyValidation> } | null)?.data ?? {};
  return {
    valid: body.valid ?? false,
    total_processes: body.total_processes ?? 0,
    errors: body.errors ?? [],
    source: body.source ?? "",
  };
}

/**
 * Reload processes.yaml into the running service.
 *
 * Safe to press, and that is worth stating in the UI rather than assuming:
 * the server validates first and keeps the current taxonomy if the new file
 * does not parse, so a bad edit degrades to "nothing changed" rather than to a
 * node that can no longer match.
 */
export async function reloadProcessTaxonomy(): Promise<number> {
  const { data, error, response } = await apiClient.POST(
    "/api/taxonomy/reload",
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Reload failed (HTTP ${response.status})`),
    );
  }
  const body =
    (data as { data?: { total_processes?: number } } | null)?.data ?? {};
  return body.total_processes ?? 0;
}

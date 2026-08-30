import { z } from "zod";
import { apiClient, ApiError, errorMessage } from "./client";
import { parsePayload } from "./parse";
import type { components } from "../generated/schema";
import type { TaxonomyProcess } from "../../features/okw/facilityFormModel";

/**
 * Generated from the route's response model — no longer hand-written here.
 *
 * Kept exported because it is this function's return type; the process shape
 * is reachable from the generated module if a caller ever needs it.
 */
export type TaxonomyValidation =
  components["schemas"]["TaxonomyValidationData"];

const TAXONOMY_PATH = "/api/taxonomy";

/**
 * The process list drives the facility form's options, so a drift here degrades
 * to a form with nothing to choose rather than to a visible error. That is the
 * case the runtime parse is for; validate and reload below are operator
 * actions whose results are read on screen, where a wrong shape shows itself.
 */
const taxonomySchema = z.looseObject({
  processes: z.array(
    z.looseObject({
      canonical_id: z.string(),
      display_name: z.string(),
      parent: z.string().nullish(),
      children: z.array(z.string()),
    }),
  ),
});

/** Load process taxonomy (processes.yaml via GET /api/taxonomy). */
export async function fetchProcessTaxonomy(): Promise<TaxonomyProcess[]> {
  const { data, error, response } = await apiClient.GET(TAXONOMY_PATH);
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load taxonomy (HTTP ${response.status})`),
    );
  }
  const payload = parsePayload(TAXONOMY_PATH, taxonomySchema, data?.data);
  return payload.processes.map((p) => ({
    canonical_id: p.canonical_id,
    display_name: p.display_name || p.canonical_id,
    parent: p.parent ?? null,
    children: p.children,
  }));
}

/** Check processes.yaml on the server's disk, without applying it. */
export async function validateProcessTaxonomy(): Promise<TaxonomyValidation> {
  const { data, error, response } = await apiClient.GET(
    "/api/taxonomy/validate",
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Validation failed (HTTP ${response.status})`),
    );
  }
  return data.data;
}

/**
 * Reload processes.yaml into the running service.
 *
 * Safe to press, and that is worth stating in the UI rather than assuming:
 * the server validates first and keeps the current taxonomy if the new file
 * does not parse, so a bad edit degrades to "nothing changed" rather than to a
 * node that can no longer match.
 *
 * Returns the process count. This read `total_processes`, which the route has
 * never returned — the field is `total` — so the settings panel reported
 * "Reloaded 0 process(es)" on every successful reload. The hand-written cast
 * is what let a name that matched nothing compile.
 */
export async function reloadProcessTaxonomy(): Promise<number> {
  const { data, error, response } = await apiClient.POST(
    "/api/taxonomy/reload",
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Reload failed (HTTP ${response.status})`),
    );
  }
  return data.data.total;
}

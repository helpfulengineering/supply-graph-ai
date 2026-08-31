import {
  apiClient,
  ApiError,
  errorMessage,
  requestIdFromError,
} from "./client";
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

/**
 * A list row. The list carries `visibility`, which the detail manifest does
 * not: `to_dict()` is a whitelist, so the payload is otherwise silent about it.
 * A caller sees shareable records plus their own, so a row that is not
 * shareable is necessarily one of the caller's own.
 */
export type OkhListItem = OkhManifest & { visibility?: VisibilityLevel };

export interface OkhListResult {
  items: OkhListItem[];
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
    items: (body.items ?? []) as OkhListItem[],
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
    throw new ApiError(
      response.status,
      "Create succeeded but response had no id",
    );
  }
  return { id: String(id) };
}

export async function getOkhProvenance(
  id: string,
): Promise<RecordProvenance | null> {
  const { data, error, response } = await apiClient.GET(
    "/api/okh/{id}/provenance",
    {
      params: { path: { id } },
    },
  );
  if (response.status === 404) return null;
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(
        error,
        `Failed to load provenance (HTTP ${response.status})`,
      ),
    );
  }
  return data;
}

export async function getOkhVisibility(
  id: string,
): Promise<VisibilityResponse> {
  const { data, error, response } = await apiClient.GET(
    "/api/okh/{id}/visibility",
    {
      params: { path: { id } },
    },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(
        error,
        `Failed to load visibility (HTTP ${response.status})`,
      ),
    );
  }
  return data;
}

export async function setOkhVisibility(
  id: string,
  visibility: VisibilityLevel,
): Promise<VisibilityResponse> {
  const { data, error, response } = await apiClient.PUT(
    "/api/okh/{id}/visibility",
    {
      params: { path: { id } },
      body: { visibility },
    },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to set visibility (HTTP ${response.status})`),
    );
  }
  return data;
}

// --- generate-from-URL ----------------------------------------------------

export interface OkhQualityReport {
  overall_quality?: string | number | null;
  required_fields_complete?: boolean | null;
  missing_required_fields?: string[] | null;
  recommendations?: string[] | null;
}

export interface GenerateOkhResult {
  success: boolean;
  message: string;
  manifest: Record<string, unknown>;
  qualityReport: OkhQualityReport | null;
}

/**
 * Generate an OKH manifest from a public repository URL.
 *
 * Synchronous by design: production has no LLM key, so generation always
 * degrades to the heuristic layers and returns within the ingress timeout.
 * Callers pass an AbortSignal — extraction can take up to about a minute and
 * the user must be able to give up.
 *
 * `verbose` is always true (it powers per-field provenance in the review step)
 * and `skip_review` is always true (the interactive review is a CLI concept;
 * this UI does its own). Neither is a user-facing option.
 *
 * `clone` is always true, and it is the difference between working and not.
 * The alternative path reads the repository over the GitHub Contents API — one
 * HTTP round trip per file — which on a substantial repository exhausts the
 * shared token's quota and exceeds the proxy timeout. Measured in production on
 * RespiraWorks/Ventilator: API path 504 after 120s, repeatedly; clone path 200
 * in 21s. A single shallow clone replaces hundreds of round trips.
 */
export async function generateOkhFromUrl(
  url: string,
  signal?: AbortSignal,
): Promise<GenerateOkhResult> {
  const { data, error, response } = await apiClient.POST(
    "/api/okh/generate-from-url",
    {
      body: { url, verbose: true, skip_review: true, clone: true } as never,
      signal,
    },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Generation failed (HTTP ${response.status})`),
      requestIdFromError(error, response),
    );
  }
  return {
    success: Boolean(data.success),
    message: String(data.message ?? ""),
    manifest: (data.manifest ?? {}) as Record<string, unknown>,
    qualityReport: (data.quality_report ?? null) as OkhQualityReport | null,
  };
}

// --- async generate-from-URL jobs -----------------------------------------

export type GenerateJobRef = components["schemas"]["OKHGenerateJobRef"];
export type GenerateJobsBatch =
  components["schemas"]["OKHGenerateJobsResponse"];
export type GenerateJobStatus = components["schemas"]["OKHGenerateJobStatus"];

/** Submit one async generation job per URL. */
export async function submitGenerateJobs(
  urls: string[],
  opts: { noLlm?: boolean } = {},
): Promise<GenerateJobsBatch> {
  const { data, error, response } = await apiClient.POST(
    "/api/okh/generate-from-url/jobs",
    {
      body: {
        urls,
        verbose: true,
        skip_review: true,
        clone: true,
        no_llm: opts.noLlm ?? false,
      },
    },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(
        error,
        `Failed to submit generation jobs (HTTP ${response.status})`,
      ),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export type GenerateJobEvents =
  components["schemas"]["OKHGenerateJobEvents"];

/**
 * The run's stage log, in order.
 *
 * Distinct from job status, which reports the stage a run is *on*: that field
 * is overwritten on every update, so polling it samples the timeline rather
 * than receiving it and a stage shorter than the interval is never seen. The
 * log is cumulative, so a poll at any rate gets everything that ran.
 *
 * Fetched whole rather than paged from a cursor. The endpoint takes `since`,
 * but a run has nine stages — carrying a cursor to save eight rows would be
 * state to keep correct for no gain.
 */
export async function getGenerateJobEvents(
  jobId: string,
): Promise<GenerateJobEvents> {
  const { data, error, response } = await apiClient.GET(
    "/api/okh/generate-from-url/jobs/{job_id}/events",
    { params: { path: { job_id: jobId }, query: { since: 0 } } },
  );
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Could not read the run log (HTTP ${response.status})`),
    );
  }
  return data as GenerateJobEvents;
}

export async function getGenerateJobStatus(
  jobId: string,
): Promise<GenerateJobStatus> {
  const { data, error, response } = await apiClient.GET(
    "/api/okh/generate-from-url/jobs/{job_id}",
    { params: { path: { job_id: jobId } } },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(
        error,
        `Failed to load job status (HTTP ${response.status})`,
      ),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export async function revokeGenerateJob(
  jobId: string,
): Promise<GenerateJobStatus> {
  const { data, error, response } = await apiClient.POST(
    "/api/okh/generate-from-url/jobs/{job_id}/revoke",
    { params: { path: { job_id: jobId } } },
  );
  if (error || !response.ok || !data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to cancel job (HTTP ${response.status})`),
      requestIdFromError(error, response),
    );
  }
  return data;
}

export type ProcessRequirement = components["schemas"]["ProcessRequirement"];

/**
 * What matching will look for in this design.
 *
 * The most useful thing to put beside a failed match: it answers "what was it
 * actually asking for?", which no other surface says out loud.
 */
export async function extractOkhRequirements(
  content: Record<string, unknown>,
): Promise<ProcessRequirement[]> {
  const { data, error, response } = await apiClient.POST("/api/okh/extract", {
    body: { content },
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(
        error,
        `Could not read requirements (HTTP ${response.status})`,
      ),
    );
  }
  return data?.requirements ?? [];
}

/**
 * A blank manifest from the server.
 *
 * The create form carries its own literal, which is a second copy of the model
 * and will drift from it. This is the authoritative shape; the literal stays
 * as the offline fallback.
 */
export async function fetchOkhTemplate(): Promise<Record<string, unknown>> {
  const { data, error, response } = await apiClient.GET("/api/okh/template");
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(
        error,
        `Could not load the template (HTTP ${response.status})`,
      ),
    );
  }
  return (data ?? {}) as Record<string, unknown>;
}

export type InventoryRow = components["schemas"]["InventoryRow"];

export interface InventoryResult {
  rows: InventoryRow[];
  total: number;
  privateTotal: number;
}

/**
 * Every record on the node, described by metadata alone.
 *
 * Admin-only, and deliberately content-free: an admin's record scope is the
 * same as anyone else's, so this is what lets an operator run the node —
 * migration, cleanup, support, takedown — without reading private records.
 */
async function fetchInventory(path: "/api/okh/inventory" | "/api/okw/inventory") {
  const { data, error, response } = await apiClient.GET(path);
  if (error || !response.ok || !data?.data) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load inventory (HTTP ${response.status})`),
    );
  }
  return {
    rows: data.data.rows ?? [],
    total: data.data.total ?? 0,
    privateTotal: data.data.private_total ?? 0,
  };
}

export function fetchOkhInventory(): Promise<InventoryResult> {
  return fetchInventory("/api/okh/inventory");
}

export function fetchOkwInventory(): Promise<InventoryResult> {
  return fetchInventory("/api/okw/inventory");
}


/**
 * Read one private record, on the record, with a reason.
 *
 * Crisis-mode only, and never a standing permission: the access is recorded as
 * an attestation naming the reader, and the record's owner can see it. The
 * caller is expected to have told the admin that before asking for a reason.
 */
export async function breakGlass(
  kind: "okh" | "okw",
  recordId: string,
  reason: string,
): Promise<unknown> {
  const path =
    kind === "okh"
      ? "/api/okh/{record_id}/break-glass"
      : "/api/okw/{record_id}/break-glass";
  const { data, error, response } = await apiClient.POST(path, {
    params: { path: { record_id: recordId } },
    body: { reason },
  });
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Break-glass refused (HTTP ${response.status})`),
    );
  }
  return data;
}

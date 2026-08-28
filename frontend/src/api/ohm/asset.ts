/**
 * Assets: physical units in the field, their triage, and salvage across them.
 *
 * Two shapes in the generated schema arrive as `{[key: string]: unknown}[]` —
 * `AssetResponse.component_states` and `SourcingResolutionItemResponse.matches`
 * — because the backend serialises them with `to_dict()` rather than a Pydantic
 * model. This module is where those close: the interfaces below mirror
 * `src/core/models/asset.py::ComponentState` and the salvage item the service
 * puts in `matches`, so nothing downstream handles a bare `unknown`.
 */
import {
  apiClient,
  ApiError,
  errorMessage,
  requestIdFromError,
} from "./client";
import type { components } from "../generated/schema";

export type AssetResponse = components["schemas"]["AssetResponse"];
export type AssetCreateRequest = components["schemas"]["AssetCreateRequest"];
export type AssetUpdateRequest = components["schemas"]["AssetUpdateRequest"];
export type AssetTriageRequest = components["schemas"]["AssetTriageRequest"];
export type TriageReport = components["schemas"]["TriageReportResponse"];
export type TriageItem = components["schemas"]["TriageItemResponse"];
export type TriageSummary = components["schemas"]["TriageSummaryResponse"];
export type TriageChecklist = components["schemas"]["ChecklistResponse"];
export type ChecklistItem = components["schemas"]["ChecklistItemResponse"];
export type SourcingResolution =
  components["schemas"]["SourcingResolutionResponse"];
export type SourcingItem =
  components["schemas"]["SourcingResolutionItemResponse"];
export type SalvageMatchRequest = components["schemas"]["SalvageMatchRequest"];
export type SalvageMatchResponse =
  components["schemas"]["SalvageMatchResponse"];
export type SalvageMatchItem =
  components["schemas"]["SalvageMatchItemResponse"];
export type ClaimComponentResponse =
  components["schemas"]["ClaimComponentResponse"];

/**
 * One recorded observation on an asset — the shape inside
 * `AssetResponse.component_states`.
 *
 * The three flags are `Optional[bool]` on the server and `null` is not `false`:
 * `_derive_action` reads "not stated" differently from "stated false", so the
 * distinction has to survive the round trip.
 */
export interface ComponentState {
  component_name: string;
  condition: string;
  repair_feasible: boolean | null;
  harvest_viable: boolean | null;
  source_required: boolean | null;
  notes: string | null;
  observed_at: string | null;
  assessed_by: string | null;
  claimed_by: string | null;
  claimed_at: string | null;
}

/** Narrow the untyped `component_states` array to what the backend puts in it. */
export function componentStates(asset: AssetResponse): ComponentState[] {
  return (asset.component_states ?? []) as unknown as ComponentState[];
}

/** Narrow the untyped `matches` array on a sourcing item. */
export function sourcingMatches(item: SourcingItem): SalvageMatchItem[] {
  return (item.matches ?? []) as unknown as SalvageMatchItem[];
}

function fail(error: unknown, response: Response, fallback: string): never {
  throw new ApiError(
    response.status,
    errorMessage(error, `${fallback} (HTTP ${response.status})`),
    requestIdFromError(error, response),
  );
}

export interface ListAssetsParams {
  manifestId?: string;
  status?: string;
  /**
   * Server-side filter to assets with harvestable components.
   *
   * Exposed because the API has it, and set by nothing. When it is on the
   * handler MUTATES each record's component_states down to the viable ones
   * before serialising, so a list rendered with it shows a different shape of
   * asset than the same list without it — a "3 of 12 assessed" count would
   * mean two different things depending on a toggle. The honest home for
   * "show me harvestable things" is salvageMatch, which returns per-component
   * rows instead of truncated assets.
   */
  harvestViable?: boolean;
}

/** List asset records, optionally scoped by design or lifecycle status. */
export async function listAssets(
  params: ListAssetsParams = {},
): Promise<{ assets: AssetResponse[]; total: number }> {
  // Trailing slash is the real path key, unlike every other domain in this app.
  const { data, error, response } = await apiClient.GET("/api/asset/", {
    params: {
      query: {
        manifest_id: params.manifestId,
        status: params.status,
        harvest_viable: params.harvestViable,
      },
    },
  });
  if (error || !response.ok || !data)
    fail(error, response, "Failed to load assets");
  return { assets: data.assets ?? [], total: data.total ?? 0 };
}

/** Fetch one asset record. */
export async function fetchAsset(id: string): Promise<AssetResponse> {
  const { data, error, response } = await apiClient.GET("/api/asset/{id}", {
    params: { path: { id } },
  });
  if (error || !response.ok || !data)
    fail(error, response, "Failed to load asset");
  return data;
}

/** Register a physical unit against a design (requires write). */
export async function createAsset(
  body: AssetCreateRequest,
): Promise<AssetResponse> {
  const { data, error, response } = await apiClient.POST("/api/asset/", {
    body,
  });
  if (error || !response.ok || !data)
    fail(error, response, "Failed to create asset");
  return data;
}

/** Update an asset's tag, location, status, or notes (requires write). */
export async function updateAsset(
  id: string,
  body: AssetUpdateRequest,
): Promise<AssetResponse> {
  const { data, error, response } = await apiClient.PUT("/api/asset/{id}", {
    params: { path: { id } },
    body,
  });
  if (error || !response.ok || !data)
    fail(error, response, "Failed to update asset");
  return data;
}

/** Delete an asset record (requires write). */
export async function deleteAsset(id: string): Promise<void> {
  const { error, response } = await apiClient.DELETE("/api/asset/{id}", {
    params: { path: { id } },
  });
  if (error || !response.ok) fail(error, response, "Failed to delete asset");
}

/**
 * Record triage observations. Upsert semantics: a component named here replaces
 * whatever was recorded for it before, and one omitted is left alone.
 */
export async function recordTriage(
  id: string,
  body: AssetTriageRequest,
): Promise<AssetResponse> {
  const { data, error, response } = await apiClient.POST(
    "/api/asset/{id}/triage",
    {
      params: { path: { id } },
      body,
    },
  );
  if (error || !response.ok || !data)
    fail(error, response, "Failed to record triage");
  return data;
}

/** The manifest's component list, pre-filled with any recorded observations. */
export async function fetchTriageChecklist(
  id: string,
): Promise<TriageChecklist> {
  const { data, error, response } = await apiClient.GET(
    "/api/asset/{id}/triage-checklist",
    { params: { path: { id } } },
  );
  if (error || !response.ok || !data)
    fail(error, response, "Failed to load checklist");
  return data;
}

/** Recorded observations turned into a recommended action per component. */
export async function fetchTriageReport(id: string): Promise<TriageReport> {
  const { data, error, response } = await apiClient.GET(
    "/api/asset/{id}/triage-report",
    { params: { path: { id } } },
  );
  if (error || !response.ok || !data)
    fail(error, response, "Failed to load report");
  return data;
}

/**
 * Where the parts this asset needs could come from.
 *
 * A GET, unlike the triage POST beside it. Expensive by construction: it builds
 * the triage report and then runs one fleet-wide salvage scan per component
 * marked source_new, so it is fetched on demand rather than with the page.
 */
export async function resolveSourcing(id: string): Promise<SourcingResolution> {
  const { data, error, response } = await apiClient.GET(
    "/api/asset/{id}/resolve-sourcing",
    { params: { path: { id } } },
  );
  if (error || !response.ok || !data)
    fail(error, response, "Failed to resolve sourcing");
  return data;
}

/** Find harvestable components across the fleet. */
export async function salvageMatch(
  body: SalvageMatchRequest,
): Promise<SalvageMatchResponse> {
  const { data, error, response } = await apiClient.POST(
    "/api/asset/salvage-match",
    {
      body,
    },
  );
  if (error || !response.ok || !data)
    fail(error, response, "Salvage search failed");
  return data;
}

/**
 * Reserve a component on an asset for retrieval.
 *
 * A 409 here is a normal outcome, not a fault: claims expire after 48h and the
 * server checks that lazily on read, so a payload can say "unclaimed" for
 * something claimed a moment ago. The status rides on the ApiError so the
 * caller can render the race as state rather than as a failure.
 */
export async function claimComponent(
  id: string,
  componentName: string,
  claimedBy: string,
): Promise<ClaimComponentResponse> {
  const { data, error, response } = await apiClient.POST(
    "/api/asset/{id}/claim-component",
    {
      params: { path: { id } },
      body: { component_name: componentName, claimed_by: claimedBy },
    },
  );
  if (error || !response.ok || !data)
    fail(error, response, "Failed to claim component");
  return data;
}

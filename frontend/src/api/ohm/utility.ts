import { apiClient, ApiError, errorMessage } from "./client";
import type { components } from "../generated/schema";

/**
 * Generated from the route's response model (#373).
 *
 * `id` is the key the API matches on; `name` is for reading. Nothing declared
 * that before, which is how the match view came to send the second where the
 * first was required (#369).
 */
export type Domain = components["schemas"]["Domain"];

/** Available matching domains (manufacturing, cooking, …). */
export async function fetchDomains(): Promise<Domain[]> {
  const { data, error, response } = await apiClient.GET("/api/utility/domains");
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load domains (HTTP ${response.status})`),
    );
  }
  return data?.data.domains ?? [];
}

/**
 * Server-configured default domain (`OHM_DEFAULT_DOMAIN`) for first-time
 * visitors — e.g. a cooking-domain instance can default new browsers to
 * "cooking" instead of the hardcoded "manufacturing" fallback. Returns null on
 * any failure rather than throwing, since callers treat this as a
 * nice-to-have seed, not a hard requirement.
 */
export async function fetchDefaultDomain(): Promise<string | null> {
  try {
    const { data, error, response } = await apiClient.GET("/api/utility/domains");
    if (error || !response.ok) return null;
    return data?.data.default_domain ?? null;
  } catch {
    return null;
  }
}

export interface SystemMetrics {
  total_requests: number;
  recent_requests_1h: number;
  active_requests: number;
  total_errors: number;
}

/** System metrics for the dashboard health panel. */
export async function fetchMetrics(): Promise<SystemMetrics> {
  const { data, error, response } = await apiClient.GET("/api/utility/metrics");
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load metrics (HTTP ${response.status})`),
    );
  }
  const d =
    (
      data as {
        data?: {
          total_requests?: number;
          recent_requests_1h?: number;
          active_requests?: number;
          error_summary?: { total_errors?: number };
        };
      }
    )?.data ?? {};
  return {
    total_requests: d.total_requests ?? 0,
    recent_requests_1h: d.recent_requests_1h ?? 0,
    active_requests: d.active_requests ?? 0,
    total_errors: d.error_summary?.total_errors ?? 0,
  };
}

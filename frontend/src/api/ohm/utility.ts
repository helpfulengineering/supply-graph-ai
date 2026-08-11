import { apiClient, ApiError, errorMessage } from "./client";

export interface Domain {
  id: string;
  name: string;
  description?: string | null;
}

/** Available matching domains (manufacturing, cooking, …). */
export async function fetchDomains(): Promise<Domain[]> {
  const { data, error, response } = await apiClient.GET("/api/utility/domains");
  if (error || !response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(error, `Failed to load domains (HTTP ${response.status})`),
    );
  }
  return ((data as { data?: { domains?: Domain[] } })?.data?.domains ?? []) as Domain[];
}

/**
 * Server-configured default domain (`OHM_DEFAULT_DOMAIN`) for first-time
 * visitors — e.g. a cooking-domain instance can default new browsers to
 * "cooking" instead of the hardcoded "manufacturing" fallback. Not yet in the
 * generated schema (the endpoint returns a plain dict), so read defensively;
 * returns null on any failure rather than throwing, since callers treat this
 * as a nice-to-have seed, not a hard requirement.
 */
export async function fetchDefaultDomain(): Promise<string | null> {
  try {
    const { data, error, response } = await apiClient.GET("/api/utility/domains");
    if (error || !response.ok) return null;
    const value = (data as { data?: { default_domain?: unknown } })?.data?.default_domain;
    return typeof value === "string" ? value : null;
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
  const d = (data as {
    data?: {
      total_requests?: number;
      recent_requests_1h?: number;
      active_requests?: number;
      error_summary?: { total_errors?: number };
    };
  })?.data ?? {};
  return {
    total_requests: d.total_requests ?? 0,
    recent_requests_1h: d.recent_requests_1h ?? 0,
    active_requests: d.active_requests ?? 0,
    total_errors: d.error_summary?.total_errors ?? 0,
  };
}

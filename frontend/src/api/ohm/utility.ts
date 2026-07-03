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

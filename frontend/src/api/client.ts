/**
 * Base HTTP client for the OHM API.
 *
 * All requests go through /v1/api (proxied to OHM_API_BASE_URL in dev; point
 * to the real origin in production). No auth in this phase.
 */

const API_PREFIX = "/v1/api";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { message?: string; detail?: string };
      message = body.message ?? body.detail ?? message;
    } catch {
      // ignore parse error; keep the HTTP status message
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

export async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(`${API_PREFIX}${path}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  return handleResponse<T>(res);
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const url = `${API_PREFIX}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

/** Returns a fully-qualified API URL for artifact links (reports, downloads). */
export function apiUrl(path: string): string {
  return `${API_PREFIX}${path}`;
}

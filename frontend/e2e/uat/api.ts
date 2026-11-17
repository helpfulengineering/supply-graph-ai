import { uatEnv } from "./env";

/**
 * Authenticated HTTP against the API under test.
 *
 * `ohm okh` sends no Authorization header, so create, visibility, attribution,
 * export and import go through this helper with an explicit bearer token. The
 * identity CLI is still used wherever the runbook uses it, so service, API and
 * CLI parity is exercised, not assumed.
 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api(
  token: string,
  method: string,
  path: string,
  body?: unknown,
  serverUrl?: string,
): Promise<{ status: number; json: unknown; text: string }> {
  const base = serverUrl ?? uatEnv().apiUrl;
  const url = `${base}/v1${path.startsWith("/") ? path : `/${path}`}`;
  const init: RequestInit = {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
  };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }
  const response = await fetch(url, init);
  const text = await response.text();
  let json: unknown = null;
  if (text) {
    try {
      json = JSON.parse(text);
    } catch {
      json = null;
    }
  }
  return { status: response.status, json, text };
}

/** Like `api`, but throws ApiError on a non-2xx response. */
export async function apiOk(
  token: string,
  method: string,
  path: string,
  body?: unknown,
  serverUrl?: string,
): Promise<unknown> {
  const result = await api(token, method, path, body, serverUrl);
  if (result.status < 200 || result.status >= 300) {
    throw new ApiError(
      result.status,
      `${method} ${path} → HTTP ${result.status}: ${result.text.slice(0, 400)}`,
    );
  }
  return result.json;
}

export function jsonField(data: unknown, name: string): string {
  if (!data || typeof data !== "object") {
    throw new ApiError(0, `expected an object with "${name}"`);
  }
  const value = (data as Record<string, unknown>)[name];
  if (value === undefined || value === null || value === "") {
    throw new ApiError(0, `expected "${name}" in the response`);
  }
  return String(value);
}

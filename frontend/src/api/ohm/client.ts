/**
 * Typed OHM API client (module 1 of the frontend architecture).
 *
 * Built on `openapi-fetch` over the types generated from the backend OpenAPI
 * spec (`src/api/generated/schema.d.ts`). Paths, query params, and response
 * envelopes are type-checked against the real contract, so backend drift is a
 * compile error. Per-domain wrappers (e.g. `okh.ts`) live alongside this and
 * expose small, intention-revealing functions to the rest of the app.
 *
 * The generated `paths` are rooted at `/api/...`; the versioned app is mounted
 * at `/v1` (proxied to the OHM API in dev), so the base URL is `/v1`.
 */
import createClient from "openapi-fetch";
import type { paths } from "../generated/schema";

// Absolute base so requests work identically in the browser (real origin +
// dev-proxy) and in the node/jsdom test env, where undici's fetch rejects
// relative URLs. In a browser this resolves to the current origin + /v1.
const origin =
  typeof window !== "undefined" && window.location?.origin
    ? window.location.origin
    : "http://localhost";

/** Versioned API base (origin + /v1). Exported for the rare call that must
 * bypass the generated client — e.g. an endpoint not yet in the committed
 * schema. Prefer `apiClient` (typed) for everything covered by the spec. */
export const apiBaseUrl = `${origin}/v1`;

export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl,
  // Defer to the *current* global fetch on each call rather than the reference
  // captured at module load, so test-time interceptors (MSW) that replace
  // globalThis.fetch after import are honored. No-op difference in the browser.
  fetch: (input) => globalThis.fetch(input),
});

/** Thrown by domain wrappers when a request fails; carries the HTTP status. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Extract request_id from an OHM error envelope or response header. */
export function requestIdFromError(
  body: unknown,
  response: Response,
): string | undefined {
  const header = response.headers.get("x-request-id");
  if (header) return header;
  if (body && typeof body === "object") {
    const id = (body as { request_id?: unknown }).request_id;
    if (typeof id === "string" && id.trim()) return id;
  }
  return undefined;
}

/** Best-effort human message from a JSON error body ({message} or {detail}). */
export function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const b = body as {
      message?: unknown;
      detail?: unknown;
      errors?: Array<{ message?: unknown }>;
    };
    if (typeof b.detail === "string") return b.detail;
    if (typeof b.message === "string") return b.message;
    const first = b.errors?.[0]?.message;
    if (typeof first === "string") return first;
  }
  return fallback;
}

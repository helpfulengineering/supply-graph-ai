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

export const apiClient = createClient<paths>({
  baseUrl: `${origin}/v1`,
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
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Best-effort human message from a JSON error body ({message} or {detail}). */
export function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const b = body as { message?: unknown; detail?: unknown };
    if (typeof b.message === "string") return b.message;
    if (typeof b.detail === "string") return b.detail;
  }
  return fallback;
}

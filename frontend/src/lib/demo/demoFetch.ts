"use client";

import { resolveDemoRoute } from "./routes";
import { demoModeEnabled } from "./demoMode";

/**
 * The demo data source: one fetch wrapper, installed once.
 *
 * All the decisions are in `routes.ts` — which request the demo world answers
 * and with what — so that they can be tested without replacing
 * `globalThis.fetch`. What is left here is the boundary itself: read the method
 * and the path off whatever shape the caller passed, hand them over, and turn
 * the answer back into a `Response`.
 *
 * The swap happens once, at this boundary, so no component, hook, or query
 * knows the source changed. Every `if (demo)` avoided is a divergence never
 * debugged.
 */

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json" },
  });
}

let installed = false;

export function installDemoFetch(): void {
  if (installed || typeof window === "undefined") return;
  if (!demoModeEnabled()) return;
  installed = true;

  const realFetch = globalThis.fetch.bind(globalThis);

  globalThis.fetch = async (input, init) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    const { pathname } = new URL(url, window.location.origin);
    // A Request carries its own method; a string URL leaves it to `init`, and
    // the default is GET. Reading it from the wrong place is how every write
    // in demo mode came back as a read of the same path.
    const method =
      init?.method ??
      (typeof input === "object" && "method" in input ? input.method : "GET");

    const route = resolveDemoRoute(method, pathname);
    if (route.kind === "json") return json(route.body);
    if (route.kind === "error") {
      // The envelope the API uses for a refusal, so `errorMessage` reads the
      // detail out of it exactly as it would from a real instance.
      return json({ detail: route.detail }, route.status);
    }
    return realFetch(input, init);
  };
}

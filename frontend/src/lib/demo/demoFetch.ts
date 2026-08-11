"use client";

import { resolveDemoRoute } from "./routes";
import { DEMO_TOKEN, demoModeEnabled } from "./demoMode";
import { getToken, setToken } from "../../features/auth/tokenStorage";

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

/**
 * Give the demo session a token, so the pages behind the admin gate are
 * reachable at all.
 *
 * `RequireAdmin` gates on a stored token — with none, `whoami` is never asked
 * and every /settings subtab redirects to the dashboard. So the demo world had
 * fixtures for keys, accounts, grants, identities, bindings and the rest that
 * no visitor could ever get to; toggling "Demo data" and clicking Settings
 * bounced you home.
 *
 * This is not a way past authentication. It is only set when the visitor has
 * explicitly switched the data source to the sample world, and in that mode
 * `resolveDemoRoute` is the only thing that ever sees the header: no request
 * leaves the browser, the whoami it answers is a fixture, and every write is
 * refused. `setDemoMode(false)` clears it before the reload, so the token
 * cannot outlive the demo and be sent to a real instance.
 *
 * It does not overwrite a real key. Someone with a live session who toggles
 * demo data on and back off keeps the session they arrived with.
 */
function seedDemoToken(): void {
  try {
    if (!getToken()) setToken(DEMO_TOKEN);
  } catch {
    // sessionStorage can be unavailable (private mode, blocked cookies). The
    // catalogue still works; only the admin subtabs stay out of reach.
  }
}

export function installDemoFetch(): void {
  if (installed || typeof window === "undefined") return;
  if (!demoModeEnabled()) return;
  installed = true;
  seedDemoToken();

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

"use client";

import { clearToken, getToken } from "../../features/auth/tokenStorage";

/**
 * Demo mode — an optional data SOURCE, not a branch through the app.
 *
 * A visitor landing on an empty instance can switch the data source to a
 * bundled sample world, explore the whole product, and switch back. This
 * mirrors the sibling monitor's "Demo data" menu action.
 *
 * The distinction that matters: nothing downstream knows about it. There is no
 * `if (demo)` in a view, a hook, or a query — the swap happens once, at the
 * fetch boundary, so every component follows the identical code path whether
 * the bytes came from the API or from the fixtures. Every `if (demo)` avoided
 * is a divergence never debugged.
 *
 * Server-seeded demo data (`make seed-demo`) is the other, independent way to
 * get a demo world, and is what an operator running a public demo should use.
 * This one needs no backend at all.
 */

const KEY = "ohm-demo-mode";

/**
 * The session token demo mode holds while it is on.
 *
 * Named rather than random so it is obvious in devtools what it is and that it
 * authorises nothing: in demo mode no request reaches the network, and the
 * sample world refuses every write regardless of what the header says. See
 * `seedDemoToken` in demoFetch.ts for why a token has to exist at all.
 */
export const DEMO_TOKEN = "demo-mode-not-a-real-key";

export function demoModeEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function setDemoMode(on: boolean): void {
  try {
    if (on) localStorage.setItem(KEY, "1");
    else localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
  // Switching off takes the demo token with it. Left behind, it would be sent
  // as a Bearer header to a real instance on the very next request — which
  // would be rejected, but as a puzzling 401 on a session the visitor never
  // knowingly started.
  try {
    if (!on && getToken() === DEMO_TOKEN) clearToken();
  } catch {
    // ignore
  }
  // Full reload rather than cache invalidation: the source changed underneath
  // every query, and a reload is the one operation guaranteed to leave no
  // half-real, half-sample state behind.
  if (typeof window !== "undefined") window.location.reload();
}

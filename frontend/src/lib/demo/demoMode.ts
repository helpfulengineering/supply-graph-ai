"use client";

import { QUERY_CACHE_KEY } from "../../queryClient";

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
  // Drop the dehydrated cache, THEN reload.
  //
  // The reload alone was the whole plan here, on the reasoning that the source
  // had changed underneath every query and a reload leaves no half-real,
  // half-sample state behind. It does not: the query client is wrapped in a
  // persister that writes every successful result to localStorage and
  // rehydrates it on boot, so the reload restored the exact state it was meant
  // to escape. Switching demo data off left the dashboard showing the sample
  // world's seven facilities and "Maps of Making unavailable" indefinitely,
  // against an instance that was answering with three thousand — with the
  // Demo data badge gone, so nothing on the page said why.
  //
  // Both directions matter. On the way in, a real catalogue must not linger
  // behind the demo badge; on the way out, the sample world must not outlive
  // it.
  try {
    localStorage.removeItem(QUERY_CACHE_KEY);
  } catch {
    // ignore
  }
  if (typeof window !== "undefined") window.location.reload();
}

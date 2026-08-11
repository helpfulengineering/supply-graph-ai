"use client";

import { fixturesByPath } from "../../test/fixtures";
import { demoModeEnabled } from "./demoMode";

/**
 * The demo data source: one fetch wrapper, installed once.
 *
 * It reuses `fixturesByPath` — the same sample world the mocked Playwright lane
 * and the MSW unit tests already run against. One sample world, three
 * consumers: a second one would drift from the first and nobody would notice
 * until a demo looked wrong.
 *
 * Anything the map does not cover falls through to the real network, so an
 * instance that *does* have data still serves it and the demo degrades to a
 * partial overlay rather than a blank page.
 */

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

    const fixture = fixturesByPath[pathname];
    if (fixture !== undefined) {
      return new Response(JSON.stringify(fixture), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }
    return realFetch(input, init);
  };
}

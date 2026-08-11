"use client";

import { fixturesByPath } from "../../test/fixtures";
import {
  demoNetworkSpaces,
  demoOkhDetail,
  demoOkhList,
  demoOkwDetail,
  demoOkwSearch,
} from "./world";
import { demoModeEnabled } from "./demoMode";

/**
 * The demo data source: one fetch wrapper, installed once.
 *
 * The catalog comes from `world.ts`, generated from scripts/seed_demo_data.py,
 * so the toggle shows exactly what `make seed-demo` puts in an instance — a
 * visitor comparing a hosted demo against their own seeded instance must not
 * find two different catalogs.
 *
 * Everything else falls back to `fixturesByPath`, the sample world the mocked
 * Playwright lane and the MSW unit tests already run against, which covers the
 * settings, identity, package, and supply-tree surfaces the seed dataset has no
 * opinion about. Anything neither map covers falls through to the real network,
 * so an instance that *does* have data still serves it.
 */

function json(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
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

    // Detail routes first: they are parameterised, so they cannot be plain
    // keys in a lookup table.
    const okhDetail = pathname.match(/^\/v1\/api\/okh\/([^/]+)$/)?.[1];
    if (okhDetail && okhDetail in demoOkhDetail) {
      return json((demoOkhDetail as Record<string, unknown>)[okhDetail]);
    }
    const okwDetail = pathname.match(/^\/v1\/api\/okw\/([^/]+)$/)?.[1];
    if (okwDetail && okwDetail in demoOkwDetail) {
      return json((demoOkwDetail as Record<string, unknown>)[okwDetail]);
    }

    const seeded: Record<string, unknown> = {
      "/v1/api/okh": demoOkhList,
      "/v1/api/okw/search": demoOkwSearch,
      "/v1/api/okw/spaces": demoNetworkSpaces,
    };
    if (pathname in seeded) return json(seeded[pathname]);

    const fixture = fixturesByPath[pathname];
    if (fixture !== undefined) return json(fixture);
    return realFetch(input, init);
  };
}

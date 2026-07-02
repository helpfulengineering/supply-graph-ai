/**
 * Shared mock API fixtures.
 *
 * Single source of truth for mocked responses, consumed by BOTH the MSW node
 * server (vitest unit/component tests) and the Playwright mocked E2E lane. Keep
 * fixtures minimal and representative; feature slices extend this as they add
 * journeys.
 */

export const healthFixture = {
  status: "ok",
  domains: ["cooking", "manufacturing"],
  version: "0.0.0-test",
};

export const domainsFixture = {
  domains: ["manufacturing", "cooking"],
};

/** Empty OKH list — exercises the empty-state path deterministically. */
export const okhListFixture = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
};

/** Path-keyed lookup used by the Playwright interceptor (see e2e/mock-api.ts). */
export const fixturesByPath: Record<string, unknown> = {
  "/health": healthFixture,
  "/v1/api/utility/domains": domainsFixture,
  "/v1/api/okh": okhListFixture,
};

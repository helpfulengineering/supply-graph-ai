import { test as base, expect } from "@playwright/test";
import { fixturesByPath } from "../src/test/fixtures";

/**
 * Playwright test extended so the `mocked` project auto-intercepts OHM API
 * calls with shared fixtures (single source of truth with the MSW node tests).
 * The `real-api` project performs no interception and hits the live backend
 * through the dev-server proxy.
 */
export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    if (testInfo.project.name === "mocked") {
      const fulfill = async (route: import("@playwright/test").Route) => {
        const pathname = new URL(route.request().url()).pathname;
        const body = fixturesByPath[pathname] ?? {};
        await route.fulfill({ json: body });
      };
      await page.route("**/v1/api/**", fulfill);
      await page.route("**/health", fulfill);
    }
    await use(page);
  },
});

export { expect };

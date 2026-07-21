import { test as base, expect } from "@playwright/test";
import { attestationsFixture, fixturesByPath, pinRecordFixture } from "../src/test/fixtures";

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
        const url = new URL(route.request().url());
        const pathname = url.pathname;
        const method = route.request().method();

        if (method === "POST" && /\/api\/package\/.+\/pin$/.test(pathname)) {
          await route.fulfill({
            json: {
              status: "success",
              message: "pinned",
              data: { pin_record: pinRecordFixture },
            },
          });
          return;
        }
        if (method === "POST" && pathname.endsWith("/api/identity/attestations/certify")) {
          await route.fulfill({ json: attestationsFixture[0], status: 201 });
          return;
        }
        if (pathname.startsWith("/v1/api/identity/reputation/")) {
          await route.fulfill({ json: attestationsFixture });
          return;
        }

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

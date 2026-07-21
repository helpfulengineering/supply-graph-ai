import { test as base, expect } from "@playwright/test";
import {
  attestationsFixture,
  bindingsFixture,
  directoryFixture,
  domainBindStartFixture,
  federationPeersFixture,
  federationSyncFixture,
  fixturesByPath,
  pinRecordFixture,
} from "../src/test/fixtures";

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
        if (method === "POST" && pathname.endsWith("/api/identity/bindings/domain/verify")) {
          await route.fulfill({
            json: {
              ...domainBindStartFixture.binding,
              verified: true,
              challenge: null,
            },
          });
          return;
        }
        if (method === "POST" && pathname.endsWith("/api/identity/bindings/domain")) {
          await route.fulfill({ json: domainBindStartFixture, status: 201 });
          return;
        }
        if (method === "POST" && pathname.endsWith("/api/identity/bindings/oauth")) {
          await route.fulfill({ json: bindingsFixture[0], status: 201 });
          return;
        }
        if (method === "POST" && pathname.endsWith("/api/identity/directory")) {
          await route.fulfill({ json: directoryFixture[0], status: 201 });
          return;
        }
        if (method === "POST" && pathname.endsWith("/api/federation/sync/run")) {
          await route.fulfill({ json: federationSyncFixture });
          return;
        }
        if (method === "POST" && pathname.endsWith("/api/federation/peers/discover")) {
          await route.fulfill({
            json: {
              updated: federationPeersFixture.peers,
              peers: federationPeersFixture.peers,
              total: federationPeersFixture.total,
            },
          });
          return;
        }
        if (method === "POST" && /\/api\/federation\/peers\/.+\/follow$/.test(pathname)) {
          await route.fulfill({
            json: { did: federationPeersFixture.peers[0]!.did, followed: true },
          });
          return;
        }
        if (method === "DELETE" && /\/api\/federation\/peers\/.+\/follow$/.test(pathname)) {
          await route.fulfill({
            json: { did: federationPeersFixture.peers[0]!.did, followed: false },
          });
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

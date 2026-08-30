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
  registrationFixture,
} from "../src/test/fixtures";

/**
 * Playwright test extended so every deterministic project auto-intercepts OHM
 * API calls with shared fixtures (single source of truth with the MSW node
 * tests). `real-api` is the one lane that performs no interception and hits the
 * live backend through the dev-server proxy.
 *
 * Named for the lane that does NOT mock, because naming the ones that do got it
 * wrong twice. The condition was `=== "mocked"`, so the two lanes added later
 * silently ran against whatever was on :8001 — nothing, in a normal checkout.
 * `responsive` measured "Something went wrong / path.id: Input should be a
 * valid UUID" on every detail route and reported the error panel as a clean
 * layout; `readme-assets` says in its own docstring that the mocked lane
 * supplies its data and it was capturing the same error panels into the
 * README's screenshots. A new lane should have to opt OUT of determinism.
 */
export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    if (testInfo.project.name !== "real-api") {
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
        if (method === "POST" && pathname.endsWith("/api/identity/register")) {
          await route.fulfill({ json: registrationFixture, status: 201 });
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

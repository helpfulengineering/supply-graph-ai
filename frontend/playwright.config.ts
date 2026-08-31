import { defineConfig, devices } from "@playwright/test";
import { readFileSync } from "node:fs";

// Read project-specific values from the reusable harness config.
const harness = JSON.parse(
  readFileSync(new URL("./harness.config.json", import.meta.url), "utf-8"),
) as { appStartCommand: string; appUrl: string };

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./artifacts/test-results",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "artifacts/playwright-report", open: "never" }],
  ],
  use: {
    baseURL: harness.appUrl,
    trace: "on-first-retry",
  },
  projects: [
    // Default lane: deterministic, MSW-style mocked API. No backend required.
    {
      name: "mocked",
      // demo-data asserts records seeded into a live backend by
      // scripts/seed_demo_data.py; there is nothing for it to assert here.
      // responsive belongs to the `mobile` lane below — running it here would
      // measure a 1280px viewport and assert nothing about the phone layout.
      // readme-assets asserts nothing at all: it captures the four images the
      // README embeds, and it is run on demand. Left in the default lane it
      // rewrote four committed binaries on every run, so an unrelated frontend
      // change arrived with four modified screenshots attached.
      testIgnore:
        /demo-data\.spec\.ts|responsive\.spec\.ts|readme-assets\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
    // Narrow-viewport lane. Every other lane is Desktop Chrome at 1280px, so
    // behaviour below 640px was asserted nowhere; this is where the small
    // layout is a gate rather than a hope. Scoped to responsive.spec.ts on
    // purpose — it asserts viewport-level properties that hold for any page,
    // so re-running the feature journeys here would cost minutes to prove
    // nothing new. The spec sets its own viewport per width.
    //
    // Desktop Chrome rather than devices["Pixel 7"], which is the intuitive
    // choice and the wrong one: Chrome's mobile emulation applies Android's
    // form-control metrics, which silently round a 13x13 checkbox and a 16px
    // text button up past the WCAG minimum. Emulating the phone therefore
    // hides the very defects this lane exists to find, and they are real for
    // anyone driving a pointer. Narrow-window desktop is the stricter
    // measurement, and a layout that survives it survives the phone.
    {
      name: "responsive",
      testMatch: /responsive\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
    // Opt-in lane: real OHM API via the dev-server proxy. Run on demand / in CI.
    {
      name: "real-api",
      testIgnore:
        /screenshots\.spec\.ts|responsive\.spec\.ts|readme-assets\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
    /**
     * Opt-in lane: regenerate the four images the README embeds.
     *
     *     npx playwright test --project=assets
     *
     * Its own project rather than a file the other lanes skip, because a
     * skipped file cannot be run by naming it — `testIgnore` wins over a path
     * argument, so excluding it everywhere would have made it unrunnable. This
     * captures rather than asserts: it writes committed binaries, which is
     * exactly why it must never be part of `npm run e2e`. It was, once, and an
     * unrelated frontend change arrived with four rewritten screenshots
     * attached and nothing to say why.
     */
    {
      name: "assets",
      testMatch: /readme-assets\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: harness.appStartCommand,
    url: harness.appUrl,
    // Reuse a running server for hand-run specs — it is the fast path while
    // iterating — but never inside `frontend-ready`. The gate builds and then
    // serves that build; silently attaching to a stray `next dev` would put
    // lazy per-route compilation back under parallel load, which is what made
    // unrelated specs time out, and would test code the build never saw.
    reuseExistingServer: !process.env.CI && !process.env.OHM_GATE,
    timeout: 120_000,
  },
});

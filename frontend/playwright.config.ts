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
      testIgnore: /demo-data\.spec\.ts|responsive\.spec\.ts/,
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
      testIgnore: /screenshots\.spec\.ts|responsive\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: harness.appStartCommand,
    url: harness.appUrl,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});

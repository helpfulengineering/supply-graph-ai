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
  reporter: [["list"], ["html", { outputFolder: "artifacts/playwright-report", open: "never" }]],
  use: {
    baseURL: harness.appUrl,
    trace: "on-first-retry",
  },
  projects: [
    // Default lane: deterministic, MSW-style mocked API. No backend required.
    {
      name: "mocked",
      use: { ...devices["Desktop Chrome"] },
    },
    // Opt-in lane: real OHM API via the dev-server proxy. Run on demand / in CI.
    {
      name: "real-api",
      testIgnore: /screenshots\.spec\.ts/,
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

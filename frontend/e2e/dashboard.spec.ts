import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

// Slice #196 + review #1: dashboard / home with the network map as the hero.

test("dashboard shows the network map, getting-started, and recent solutions", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /open hardware manager/i })).toBeVisible();
  // Map hero + onboarding replace the old nav-duplicate journey cards.
  await expect(page.getByRole("heading", { name: /manufacturing network/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /getting started/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /recent solutions/i })).toBeVisible();
});

test("dashboard summarizes the map, stats, and health (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/");
  // Map summary line derived from the fixture counts (incl. the dropped-coords note).
  await expect(page.getByText(/2 OHM facilities/)).toBeVisible();
  await expect(page.getByText(/without coordinates not shown/)).toBeVisible();
  // Source legend.
  await expect(page.getByText("Maps of Making", { exact: true }).first()).toBeVisible();
  // Recent solution + system health from fixtures.
  await expect(page.getByText("Open Ventilator")).toBeVisible();
  await expect(page.getByText(/api online/i)).toBeVisible();
});

test("dashboard falls back to local-only when MoM is unavailable (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces a MoM-unavailable response");
  await page.route("**/v1/api/okw/map**", (route) =>
    route.fulfill({
      json: {
        success: true,
        points: [{ id: "okw-1", name: "Laser Fab Lab", lat: 30.27, lon: -97.74, source: "local" }],
        local_count: 1,
        mom_count: 0,
        dropped_no_coords: 0,
        mom_available: false,
      },
    }),
  );
  await page.goto("/");
  await expect(page.getByText(/Maps of Making unavailable/)).toBeVisible();
});

test("dashboard has no serious accessibility violations", async ({ page }) => {
  await page.goto("/");
  await expectNoA11yViolations(page);
});

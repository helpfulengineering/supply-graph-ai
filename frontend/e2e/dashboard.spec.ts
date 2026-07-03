import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

// Slice #196: dashboard / home.

test("dashboard shows journeys, recent solutions, and health", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /open hardware manager/i })).toBeVisible();
  // Journey entry points.
  await expect(page.getByRole("link", { name: /designs/i }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /recent solutions/i })).toBeVisible();
});

test("dashboard surfaces recent solutions and domains (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/");
  // Recent solution from the fixture.
  await expect(page.getByText("Open Ventilator")).toBeVisible();
  // System health: online + a domain badge.
  await expect(page.getByText(/api online/i)).toBeVisible();
  await expect(page.getByText("Manufacturing", { exact: true })).toBeVisible();
});

test("dashboard has no serious accessibility violations", async ({ page }) => {
  await page.goto("/");
  await expectNoA11yViolations(page);
});

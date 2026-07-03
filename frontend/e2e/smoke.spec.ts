import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

// Phase 0 smoke: proves the app shell renders and the a11y scan runs. Runs in
// both the mocked lane (default gate) and the real-api lane.
test("home page renders the app shell", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /open hardware manager/i }),
  ).toBeVisible();
  // Navigation shell present (brand link).
  await expect(page.getByRole("link", { name: "OHM" })).toBeVisible();
});

test("home page has no serious accessibility violations", async ({ page }) => {
  await page.goto("/");
  await expectNoA11yViolations(page);
});

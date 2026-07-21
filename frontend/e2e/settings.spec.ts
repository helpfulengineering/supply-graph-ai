import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

test("settings redirects home without an admin session", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked whoami only");
  await page.goto("/settings/session");
  await expect(page.getByRole("heading", { name: /open hardware manager/i })).toBeVisible();
  await expect(page.getByRole("link", { name: "Settings" })).toHaveCount(0);
});

test("settings session a11y with mocked admin whoami", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked whoami only");
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });
  await page.goto("/settings/session");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "API key" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Settings" })).toBeVisible();
  await expectNoA11yViolations(page);
});

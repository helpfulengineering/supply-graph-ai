import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

test("packages list shows fixture packages and nav link", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked fixtures");
  await page.addInitScript(() => localStorage.removeItem("ohm-query-cache"));
  await page.goto("/packages");
  await expect(page.getByRole("heading", { name: "Packages" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Packages" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "demo/widget" }).first()).toBeVisible();
  await expectNoA11yViolations(page);
});

test("package detail deep link", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked fixtures");
  await page.addInitScript(() => localStorage.removeItem("ohm-query-cache"));
  await page.goto("/packages/demo/widget/1.0.0");
  await expect(page.getByRole("heading", { name: "demo/widget" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Download/i }).first()).toBeVisible();
  await expectNoA11yViolations(page);
});

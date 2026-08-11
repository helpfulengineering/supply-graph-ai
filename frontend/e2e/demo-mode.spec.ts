import { test, expect } from "./mock-api";

/**
 * Demo mode is a visitor-level toggle, off by default.
 *
 * The property worth protecting is that it is a data SOURCE and not a branch:
 * with it on, the app must render the sample world through exactly the same
 * components, queries, and code paths it uses for real data. So these specs
 * assert on ordinary product surfaces — the catalog, the chrome — rather than
 * on anything demo-specific.
 */

test("demo mode is off by default and advertises nothing", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Demo data")).toHaveCount(0);

  await page.getByRole("button", { name: "Site menu" }).click();
  const toggle = page.getByRole("button", { name: /Demo data/ });
  await expect(toggle).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
});

test("enabling demo mode surfaces the badge and the sample catalog", async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem("ohm-demo-mode", "1"));
  await page.goto("/okh");

  await expect(page.getByRole("heading", { name: "Open Ventilator" })).toBeVisible();
  // The header states the source, so a visitor is never misled about whether
  // what they are looking at is real.
  await expect(page.getByText("Demo data").first()).toBeVisible();
});

test("turning demo mode off returns to the real source", async ({ page }) => {
  // Set the flag after load rather than via addInitScript: an init script
  // re-runs on every navigation, so it would re-enable demo mode during the
  // toggle's own reload and the test would be asserting against itself.
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("ohm-demo-mode", "1"));
  await page.reload();
  await page.getByRole("button", { name: "Site menu" }).click();

  const toggle = page.getByRole("button", { name: /Demo data/ });
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await toggle.click();

  // The toggle reloads deliberately, so the source cannot be half-swapped.
  await page.waitForLoadState("networkidle");
  const stored = await page.evaluate(() => localStorage.getItem("ohm-demo-mode"));
  expect(stored).toBeNull();
});

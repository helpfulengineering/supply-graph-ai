import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

/**
 * The site layer is off by default, and "off" has to be a first-class state
 * rather than a degraded one. That is the trap this phase exists to avoid:
 * building a lovely signed-in experience and letting the default,
 * unconfigured instance become the broken-looking one.
 *
 * These specs run in the DEFAULT configuration (no Supabase env), which is the
 * deployment almost every operator will actually run. The enabled direction is
 * covered by running the suite again with the env vars set — see
 * docs/architecture/site-layer.md.
 */

test("no Mission Control entry in the sitemap when the layer is off", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Site menu" }).click();
  const nav = page.getByRole("navigation", { name: "Primary navigation" });
  await expect(nav.getByRole("link", { name: /Mission Control/ })).toHaveCount(0);
  // Absent, not present-and-disabled: a disabled entry advertises a capability
  // this instance does not have.
  await expect(nav.getByText(/Site$/)).toHaveCount(0);
});

test("Mission Control route 404s when the layer is off", async ({ page }) => {
  const response = await page.goto("/mission-control");
  expect(response?.status()).toBe(404);
});

test("no gate, and no site-layer console errors, on a default instance", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: /open hardware manager/i })).toBeVisible();
  // No sign-in gate blocks the app.
  await expect(page.getByRole("dialog", { name: /sign in/i })).toHaveCount(0);

  const siteErrors = errors.filter((e) => /supabase|ohmgr_|site layer/i.test(e));
  expect(siteErrors, `site-layer errors on a default instance:\n${siteErrors.join("\n")}`).toEqual(
    [],
  );
});

test("theme and mode still work with the layer off", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Site menu" }).click();
  await page.getByRole("radio", { name: "Terminal" }).check();
  await expect(page.locator("html")).toHaveAttribute("data-ttm-theme", "terminal");

  // Device-level preference persists without any backend.
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-ttm-theme", "terminal");
});

test("default instance chrome passes the a11y scan", async ({ page }) => {
  await page.goto("/");
  await expectNoA11yViolations(page);
});

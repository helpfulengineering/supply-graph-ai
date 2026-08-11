import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";
import { NAV_GROUPS } from "../src/components/layout/nav";

/**
 * The universal chrome: header, hamburger sitemap, footer. The contract this
 * suite enforces is the Phase 4 test — adding a page requires deciding nothing
 * about its chrome — plus the disclosure semantics the drawer promises.
 */

test("every sitemap entry renders in the drawer with its role line", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Site menu" }).click();
  const nav = page.getByRole("navigation", { name: "Primary navigation" });
  // The sitemap is data, this walk is the whole test: a page added to nav.ts
  // is in the drawer, or this fails.
  for (const group of NAV_GROUPS) {
    for (const entry of group.entries) {
      const link = nav.getByRole("link", { name: new RegExp(entry.name) });
      await expect(link).toBeVisible();
      await expect(link).toContainText(entry.desc);
    }
  }
});

test("open drawer passes the a11y scan", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Site menu" }).click();
  await expect(page.getByRole("dialog", { name: "Site menu" })).toBeVisible();
  await expectNoA11yViolations(page);
});

test("drawer traps focus, closes on Escape, and returns focus", async ({ page }) => {
  await page.goto("/");
  const burger = page.getByRole("button", { name: "Site menu" });
  await burger.click();

  // Focus lands inside the dialog (close button first).
  await expect(page.getByRole("button", { name: "Close menu" })).toBeFocused();

  // Shift+Tab from the first focusable wraps to the last — the trap, probed
  // from its edge in one step rather than tabbing through the whole sitemap.
  await page.keyboard.press("Shift+Tab");
  const wrapped = await page.evaluate(() => {
    const dialog = document.getElementById("site-menu");
    return dialog?.contains(document.activeElement) ?? false;
  });
  expect(wrapped).toBe(true);

  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Site menu" })).toHaveCount(0);
  await expect(burger).toBeFocused();
});

test("current route carries aria-current in the sitemap", async ({ page }) => {
  await page.goto("/okh");
  await page.getByRole("button", { name: "Site menu" }).click();
  const nav = page.getByRole("navigation", { name: "Primary navigation" });
  await expect(nav.getByRole("link", { name: /Designs/ })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(nav.locator('[aria-current="page"]')).toHaveCount(1);
});

test("skip link is the first tab stop and lands on main", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  // The dev server injects <nextjs-portal> (the error overlay) ahead of the
  // document and it takes one tab stop; production builds do not include it.
  // Step over it so the assertion holds in both environments.
  const onPortal = await page.evaluate(
    () => document.activeElement?.tagName === "NEXTJS-PORTAL",
  );
  if (onPortal) await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to content" });
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});

test("header and footer are universal", async ({ page }) => {
  for (const route of ["/", "/okh", "/settings/session"]) {
    await page.goto(route);
    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("contentinfo")).toContainText("made with");
    await expect(page.getByRole("contentinfo")).toContainText("by OpenSource");
  }
});

test("navigating from the drawer closes it", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Site menu" }).click();
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("link", { name: /Designs/ })
    .click();
  await expect(page).toHaveURL(/\/okh$/);
  await expect(page.getByRole("dialog", { name: "Site menu" })).toHaveCount(0);
});

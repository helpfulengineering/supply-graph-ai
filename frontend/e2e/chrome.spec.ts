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

test("skip link is the first focusable element and lands on main", async ({ page }) => {
  await page.goto("/");

  // Asserted from document order rather than by counting Tab presses: under
  // the dev server Next injects <nextjs-portal> (the error overlay) ahead of
  // the app, and its shadow root swallows focus in a way that makes
  // activeElement unreliable. Document order is the contract that actually
  // matters and it holds in both dev and production.
  // Wait for the app to be in the DOM before reading document order, or the
  // evaluate can run against a shell that holds only the dev overlay.
  await page.getByRole("link", { name: "Skip to content" }).waitFor({ state: "attached" });

  const firstFocusable = await page.evaluate(() => {
    const focusable = [
      ...document.body.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ].filter((el) => !el.closest("nextjs-portal"));
    return focusable[0]?.textContent?.trim() ?? null;
  });
  expect(firstFocusable).toBe("Skip to content");

  const skip = page.getByRole("link", { name: "Skip to content" });
  await skip.focus();
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
  // The target must exist and be focusable, or the link goes nowhere useful.
  await expect(page.locator("#main")).toHaveCount(1);
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
  // Path, not the whole URL: the look rides in the query string on every
  // route now, so `/okh?theme=…&mode=…` is the expected shape of "went to
  // the designs page".
  await expect(page).toHaveURL(/\/okh(\?|$)/);
  await expect(page.getByRole("dialog", { name: "Site menu" })).toHaveCount(0);
});

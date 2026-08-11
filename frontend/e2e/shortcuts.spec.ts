import { test, expect } from "./mock-api";
import { CHORD_ROUTES } from "../src/components/layout/shortcuts";
import type { Page } from "@playwright/test";

/** Keys pressed before hydration land on nothing; wait for the bind marker. */
async function keysReady(page: Page): Promise<void> {
  await page.waitForSelector("html[data-keys-ready]", { timeout: 15_000 });
}

/**
 * The keyboard contract. Driven from CHORD_ROUTES so a shortcut added to the
 * data file is covered here without editing this spec.
 */

test("? opens and closes the sitemap", async ({ page }) => {
  await page.goto("/");
  await keysReady(page);
  await page.keyboard.press("?");
  await expect(page.getByRole("dialog", { name: "Site menu" })).toBeVisible();
  await page.keyboard.press("?");
  await expect(page.getByRole("dialog", { name: "Site menu" })).toBeHidden();
});

test("Escape closes the drawer and returns focus to the burger", async ({ page }) => {
  await page.goto("/");
  await keysReady(page);
  const burger = page.getByRole("button", { name: "Site menu" });
  await burger.click();
  await expect(page.getByRole("dialog", { name: "Site menu" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Site menu" })).toBeHidden();
  await expect(burger).toBeFocused();
});

test("t cycles the theme and m flips the mode", async ({ page }) => {
  await page.goto("/");
  await keysReady(page);
  const world = () => page.evaluate(() => document.documentElement.dataset.ttmTheme);
  const dark = () => page.evaluate(() => document.documentElement.classList.contains("dark"));

  const before = await world();
  await page.keyboard.press("t");
  await expect.poll(world).not.toBe(before);

  const wasDark = await dark();
  await page.keyboard.press("m");
  await expect.poll(dark).toBe(!wasDark);
});

for (const [key, href] of Object.entries(CHORD_ROUTES)) {
  test(`g then ${key} navigates to ${href}`, async ({ page }) => {
    await page.goto("/");
  await keysReady(page);
    await page.keyboard.press("g");
    await page.keyboard.press(key);
    await page.waitForURL((url) => url.pathname === href, { timeout: 10_000 });
    expect(new URL(page.url()).pathname).toBe(href);
  });
}

test("shortcuts do not fire while typing", async ({ page }) => {
  await page.goto("/okh");
  await keysReady(page);
  const search = page.getByPlaceholder(/search designs/i);
  await search.click();
  const before = await page.evaluate(() => document.documentElement.dataset.ttmTheme);

  // One keystroke, not a sequence: the catalog writes every keystroke to the
  // URL, so a multi-character sequence races that round-trip under parallel
  // load and tests the debounce rather than the guard. "t" alone is enough —
  // it is a shortcut key, typed into a field.
  await page.keyboard.press("t");

  await expect(search).toHaveValue("t");
  expect(new URL(page.url()).pathname).toBe("/okh");
  expect(await page.evaluate(() => document.documentElement.dataset.ttmTheme)).toBe(
    before,
  );
});

test("/help documents every shortcut and route the chrome binds", async ({ page }) => {
  // Help is generated from NAV_GROUPS and SHORTCUTS, so this asserts the
  // contract itself rather than a hand-maintained copy of it.
  await page.goto("/help");
  await expect(page.getByRole("heading", { name: "Help" })).toBeVisible();

  for (const [key, href] of Object.entries(CHORD_ROUTES)) {
    await expect(
      page.locator("kbd", { hasText: new RegExp(`^${key}$`) }).first(),
      `shortcut key ${key} is documented`,
    ).toHaveCount(1);
    await expect(
      page.locator(`a[href="${href}"]`).first(),
      `route ${href} is listed`,
    ).toHaveCount(1);
  }

  await expect(page.getByRole("heading", { name: /accessibility/i })).toBeVisible();
});

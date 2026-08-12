import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";
import type { Page } from "@playwright/test";

/**
 * The site layer is off by default, and "off" has to be a first-class state
 * rather than a degraded one. That is the trap this phase exists to avoid:
 * building a lovely signed-in experience and letting the default,
 * unconfigured instance become the broken-looking one.
 *
 * The plan for this phase requires the suite to be green in BOTH postures —
 * run once with no Supabase env (the default) and once with it set. So these
 * specs read the posture rather than assuming one: each asserts the correct
 * behaviour for however the instance under test is configured, and the pair of
 * runs proves neither direction is the degraded one.
 *
 * Reading the same env the app reads (rather than a test-only flag) keeps the
 * The posture is read from the SERVED PAGE, not from process.env. An earlier
 * version read the runner's environment, which equals the server's only when
 * Playwright started the server itself — reusing an already-running dev server
 * made the spec assert against a posture the app was not in, and fail for
 * being right. app/providers.tsx publishes data-site-layer for exactly this.
 */

/** What posture is the app under test actually in? */
async function layerEnabled(page: Page): Promise<boolean> {
  await page.goto("/");
  // toHaveAttribute, not getAttribute. That timeout governs FINDING <html>,
  // which arrives in the first byte of the response — the attribute is written
  // by the client bundle, so the read resolves against an element that exists
  // and an attribute that does not yet, returns null, and never retries.
  //
  // A fast machine wins that race and the helper looks correct. A loaded CI
  // runner loses it, and every spec that reads the posture fails claiming the
  // app never published the attribute while the app publishes it a moment
  // later — including the ones whose only use for it is to skip. This is the
  // assertion that waits for the value rather than for the element.
  await expect(
    page.locator("html"),
    "the app did not publish data-site-layer — see app/providers.tsx",
  ).toHaveAttribute("data-site-layer", /^(on|off)$/, { timeout: 15_000 });
  return (await page.locator("html").getAttribute("data-site-layer")) === "on";
}

test("the sitemap advertises Operator Tools only when the layer is on", async ({
  page,
}) => {
  await page.goto("/");
  const enabled = await layerEnabled(page);
  await page.getByRole("button", { name: "Site menu" }).click();
  const entry = page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("link", { name: /Operator Tools/ });

  if (enabled) {
    await expect(entry).toHaveCount(1);
  } else {
    // Absent, not present-and-disabled: a disabled entry advertises a
    // capability this instance does not have.
    await expect(entry).toHaveCount(0);
  }
});

test("the Operator Tools route exists only when the layer is on", async ({
  page,
}) => {
  const enabled = await layerEnabled(page);
  const response = await page.goto("/operator-tools");
  if (enabled) {
    expect(response?.status()).toBe(200);
    await expect(
      page.getByRole("heading", { name: /operator tools/i }),
    ).toBeVisible();
  } else {
    // A real 404, not a 200 rendering a "not found" body — an undeployed
    // capability that answers 200 is how a broken route goes unnoticed.
    expect(response?.status()).toBe(404);
  }
});

test("Operator Tools gates entry, and dismissal is not a dead end", async ({
  page,
}) => {
  // The default posture has no route to gate: the test above asserts it 404s,
  // and the one below asserts — in both postures — that no gate ever blocks
  // the app itself. Re-navigating to the 404 here would add nothing.
  const enabled = await layerEnabled(page);
  test.skip(!enabled, "no Operator Tools route on a default instance");

  await page.goto("/operator-tools");
  const gate = page.getByRole("dialog");

  // Arriving without a visitor record on this device puts the gate in front of
  // the page — that is what "gate" means, and it is why the panel behind it
  // says to sign in at one.
  await expect(gate).toBeVisible();
  await expect(gate.getByRole("button", { name: "Sign in" })).toBeVisible();
  await expectNoA11yViolations(page);

  // Esc dismisses, and the page keeps a way back in. The gate stands in front
  // of this one surface, never in front of the app.
  await page.keyboard.press("Escape");
  await expect(gate).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
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
  await expect(
    page.getByRole("heading", { name: /open hardware manager/i }),
  ).toBeVisible();
  // No sign-in gate blocks the app. Asserted in BOTH postures, deliberately:
  // the gate belongs in front of Operator Tools and nowhere else, so an
  // enabled instance must still open the dashboard to anyone.
  await expect(page.getByRole("dialog", { name: /sign in/i })).toHaveCount(0);

  const siteErrors = errors.filter((e) =>
    /supabase|ohmgr_|site layer/i.test(e),
  );
  expect(
    siteErrors,
    `site-layer errors on a default instance:\n${siteErrors.join("\n")}`,
  ).toEqual([]);
});

test("theme and mode still work with the layer off", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Site menu" }).click();
  // click(), not check(). check() clicks and then asserts `checked` in the same
  // step, with no retry — and a theme change is applied inside
  // `document.startViewTransition` (see applyThemeChange in hooks/useDarkMode),
  // whose callback the browser runs a frame after the click, once it has
  // snapshotted the old page. Until that callback flushes, React re-renders the
  // controlled radio from unchanged state and returns it to unchecked, so
  // check() reads false and throws. Measured: false at the click, true 50ms
  // later. The lag is one frame of a deliberate crossfade, not a control that
  // fails to register, so the assertion belongs in expect(), which polls.
  const terminal = page.getByRole("radio", { name: "Terminal" });
  await terminal.click();
  await expect(terminal).toBeChecked();
  await expect(page.locator("html")).toHaveAttribute(
    "data-ttm-theme",
    "terminal",
  );

  // Device-level preference persists without any backend.
  //
  // The stored value is asserted before the reload, not because storage is the
  // promise — the promise is what the visitor sees after coming back — but
  // because it splits the two halves of it. Reloading on the attribute alone
  // means a failure here could be either a write that never happened or a read
  // that ignored it, and those live in different places.
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("ohm-theme")))
    .toBe("terminal");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute(
    "data-ttm-theme",
    "terminal",
  );
});

test("default instance chrome passes the a11y scan", async ({ page }) => {
  await page.goto("/");
  await expectNoA11yViolations(page);
});

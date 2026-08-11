import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

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
 * spec honest: if config.ts ever decided "enabled" differently, this would
 * assert against the wrong posture and fail rather than quietly pass.
 */

/** Mirrors the enabled test in src/lib/site/config.ts. */
const LAYER_ENABLED = Boolean(
  process.env.NEXT_PUBLIC_OHM_SUPABASE_URL &&
  process.env.NEXT_PUBLIC_OHM_SUPABASE_ANON_KEY &&
  !process.env.NEXT_PUBLIC_OHM_SUPABASE_URL.startsWith("%") &&
  !process.env.NEXT_PUBLIC_OHM_SUPABASE_ANON_KEY.startsWith("%"),
);

test("the sitemap advertises Mission Control only when the layer is on", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Site menu" }).click();
  const entry = page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("link", { name: /Mission Control/ });

  if (LAYER_ENABLED) {
    await expect(entry).toHaveCount(1);
  } else {
    // Absent, not present-and-disabled: a disabled entry advertises a
    // capability this instance does not have.
    await expect(entry).toHaveCount(0);
  }
});

test("the Mission Control route exists only when the layer is on", async ({
  page,
}) => {
  const response = await page.goto("/mission-control");
  if (LAYER_ENABLED) {
    expect(response?.status()).toBe(200);
    await expect(
      page.getByRole("heading", { name: /mission control/i }),
    ).toBeVisible();
  } else {
    // A real 404, not a 200 rendering a "not found" body — an undeployed
    // capability that answers 200 is how a broken route goes unnoticed.
    expect(response?.status()).toBe(404);
  }
});

test("Mission Control gates entry, and dismissal is not a dead end", async ({ page }) => {
  // The default posture has no route to gate: the test above asserts it 404s,
  // and the one below asserts — in both postures — that no gate ever blocks
  // the app itself. Re-navigating to the 404 here would add nothing.
  test.skip(!LAYER_ENABLED, "no Mission Control route on a default instance");

  await page.goto("/mission-control");
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
  // the gate belongs in front of Mission Control and nowhere else, so an
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
  await page.getByRole("radio", { name: "Terminal" }).check();
  await expect(page.locator("html")).toHaveAttribute(
    "data-ttm-theme",
    "terminal",
  );

  // Device-level preference persists without any backend.
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

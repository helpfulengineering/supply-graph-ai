import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";
import { BRAND_TAGLINE_LINKS } from "../app/brand";

// Slice #196 + review #1: dashboard / home with the network map as the hero.

test("dashboard shows the network map and getting-started", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /open hardware manager/i }),
  ).toBeVisible();
  // Map hero + onboarding replace the old nav-duplicate journey cards.
  // The map's section is named by aria-label rather than a visible heading —
  // a caption reading "Manufacturing network" over a map of it said nothing
  // and pushed the map down the fold. The landmark still carries the name.
  await expect(
    page.getByRole("region", { name: /manufacturing network/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /getting started/i }),
  ).toBeVisible();
});

test("dashboard summarizes the map, stats, and health (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/");
  // Map summary line derived from the fixture counts (incl. the dropped-coords note).
  await expect(page.getByText(/2 OHM facilities/)).toBeVisible();
  await expect(page.getByText(/without coordinates not shown/)).toBeVisible();
  // Source legend.
  await expect(
    page.getByText("Maps of Making", { exact: true }).first(),
  ).toBeVisible();
  // System health.
  await expect(page.getByText(/api online/i)).toBeVisible();
});

test("dashboard falls back to local-only when MoM is unavailable (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name === "real-api",
    "forces a MoM-unavailable response",
  );
  await page.route("**/v1/api/okw/spaces**", (route) =>
    route.fulfill({
      json: {
        success: true,
        spaces: [
          {
            id: "okw-1",
            name: "Laser Fab Lab",
            lat: 30.27,
            lon: -97.74,
            source: "local",
          },
        ],
        local_count: 1,
        mom_count: 0,
        dropped_no_coords: 0,
        mom_available: false,
      },
    }),
  );
  await page.goto("/");
  await expect(page.getByText(/Maps of Making unavailable/)).toBeVisible();
});

test("dashboard has no serious accessibility violations", async ({ page }) => {
  await page.goto("/");
  await expectNoA11yViolations(page);
});

/**
 * The hero crumb is navigation, not decoration.
 *
 * "designs · facilities · supply chains" sat under the h1 as dead text on the
 * page a first-time visitor lands on, naming the three things the app holds and
 * offering no way to reach any of them.
 *
 * Driven from BRAND_TAGLINE_LINKS rather than restated here, so a term added to
 * the tagline is asserted to lead somewhere instead of quietly shipping as
 * more dead text. Scoped to the page hero inside <main>: the same words appear
 * in the sitemap drawer and in Getting Started, and an unscoped role query
 * would pass on those while the crumb stayed unlinked.
 */
for (const term of BRAND_TAGLINE_LINKS) {
  test(`the hero crumb reaches "${term.label}" by Tab and follows it on Enter`, async ({
    page,
  }) => {
    await page.goto("/");
    const link = page
      .locator("#main header")
      .first()
      .getByRole("link", { name: term.label, exact: true });
    await expect(link).toBeVisible();

    // Tabbed to rather than focused with .focus(): the property under test is
    // that a keyboard reaches these at all, and focusing the element directly
    // asserts that away. Bounded so a link that never receives focus fails
    // here instead of hanging. The crumb sits fifth at most — skip link, mark,
    // mode, menu, then the terms — so 12 is headroom, not a guess at the
    // answer.
    let reached = false;
    for (let i = 0; i < 12 && !reached; i++) {
      await page.keyboard.press("Tab");
      reached = await link.evaluate((el) => el === document.activeElement);
    }
    expect(reached, `"${term.label}" was not reachable within 12 Tabs`).toBe(
      true,
    );

    // WCAG 2.4.7: focus has to be visible, not merely present. The ring is
    // drawn as a box-shadow by the focus-visible utilities, so "none" here
    // means a keyboard user is navigating an invisible cursor.
    const ring = await link.evaluate(
      (el) => getComputedStyle(el).boxShadow ?? "none",
    );
    expect(ring, `no visible focus indicator on "${term.label}"`).not.toBe(
      "none",
    );

    await page.keyboard.press("Enter");
    // Anchored on the path, not the whole URL: theme and mode ride in the
    // query string and survive navigation, so `${href}$` never matches once a
    // look has been pinned — which the mocked lane does on every goto.
    await expect(page).toHaveURL(new RegExp(`${term.href}(\\?|$)`));
  });
}

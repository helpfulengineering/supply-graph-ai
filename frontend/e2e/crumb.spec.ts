import { expect } from "@playwright/test";
import { test } from "./mock-api";

/**
 * The hero crumb, everywhere it appears, driven by keyboard.
 *
 * The terms under each h1 — "designs · facilities · supply chains",
 * "session · keys · identities" — were dead text on every page. They are links
 * now, rendered by one component (PageHero), and this is the gate that says so
 * for all of them rather than for the one view a feature spec happens to cover.
 *
 * The routes are listed; the links are NOT. Each page is asked what it renders
 * in its crumb and every link found there is exercised, so linking a new term
 * extends this gate without editing it — and so does a term that quietly stops
 * being a link, which fails the count assertion instead of passing silently.
 *
 * Discovered through `[data-crumb]` rather than "links in the hero": the
 * breadcrumb above the title and the `actions` beside it hold links of their
 * own (/okh has "Generate from URL" and "New design"), and a looser selector
 * would measure those and report green while a crumb led nowhere.
 */
const ROUTES = ["/", "/okh", "/match", "/rfq", "/help", "/visualization/sol-1"];

/**
 * Routes whose crumb is expected to carry at least one link.
 *
 * Asserted so an empty crumb cannot pass as "nothing to check". Not every term
 * names a destination — /facilities is "local · federated · filtered", three
 * descriptions of one page — so this is a floor per route, not a total.
 */
const MIN_LINKS: Record<string, number> = {
  "/": 3,
  "/okh": 1,
  "/match": 2,
  "/rfq": 1,
  "/help": 3,
  "/visualization/sol-1": 1,
};

for (const route of ROUTES) {
  test(`hero crumb links are keyboard-operable on ${route}`, async ({
    page,
  }) => {
    await page.goto(route);
    await page.locator("#main").waitFor({ state: "visible" });

    // Read every term up front, off this one load. Reading them lazily inside
    // the loop looked equivalent and was not: the previous iteration's Enter
    // has already taken the page elsewhere, so link i+1 was being read from the
    // destination rather than from the page under test — and on a destination
    // with fewer crumb links the read simply hung until the timeout.
    const terms = await page
      .locator("#main [data-crumb] a")
      .evaluateAll((els) =>
        els.map((el) => ({
          label: el.textContent?.trim() ?? "",
          href: el.getAttribute("href") ?? "",
        })),
      );
    expect(
      terms.length,
      `${route} rendered ${terms.length} crumb links, expected at least ${MIN_LINKS[route]}`,
    ).toBeGreaterThanOrEqual(MIN_LINKS[route]);

    for (const [i, { label, href }] of terms.entries()) {
      // Reloaded per link rather than navigating on and coming back: Enter
      // takes the page away, and the next link has to be reached from a fresh
      // document for the Tab count to mean anything.
      await page.goto(route);
      await page.locator("#main").waitFor({ state: "visible" });

      // Tabbed to rather than focused with .focus(): the property is that a
      // keyboard reaches these at all, which focusing directly asserts away.
      // Bounded, so a link that never takes focus fails here instead of
      // hanging.
      const target = page.locator("#main [data-crumb] a").nth(i);
      let reached = false;
      for (let tab = 0; tab < 20 && !reached; tab++) {
        await page.keyboard.press("Tab");
        reached = await target.evaluate((el) => el === document.activeElement);
      }
      expect(
        reached,
        `"${label}" on ${route} was not reachable within 20 Tabs`,
      ).toBe(true);

      // WCAG 2.4.7: focus has to be visible, not merely present. The ring is
      // drawn as a box-shadow by the focus-visible utilities and computes to
      // "none" when the element is not focused, so this only holds while the
      // indicator is actually painted.
      const ring = await target.evaluate(
        (el) => getComputedStyle(el).boxShadow,
      );
      expect(
        ring,
        `no visible focus indicator on "${label}" (${route})`,
      ).not.toBe("none");

      await page.keyboard.press("Enter");
      // `toContain` rather than a path regex: a crumb term may be an in-page
      // section (/help links #h-keys), and both forms show up in the URL.
      // Theme and mode ride in the query string and survive navigation, so
      // anchoring the end of the URL would never match.
      await expect
        .poll(() => page.url(), {
          message: `"${label}" on ${route} did not navigate to ${href}`,
        })
        .toContain(href);
    }
  });
}

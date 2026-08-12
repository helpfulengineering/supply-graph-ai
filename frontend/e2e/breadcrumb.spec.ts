import { expect } from "@playwright/test";
import { test } from "./mock-api";

/**
 * The breadcrumb trail, on every route that has one.
 *
 * Four views used to write this by hand and had drifted: three of the four
 * <nav>s carried no accessible name, none marked the leaf as the current page,
 * and the trail rendered at two different sizes depending on the route. They
 * share one component now, and these are the properties it owes.
 *
 * Target size is the reason this spec exists rather than a line in
 * responsive.spec.ts. That lane audits a route as soon as `#main` is visible,
 * which on a data-driven detail page is while the loading state is still on
 * screen — so the trail had never been measured, and the hand-rolled versions
 * were shipping 20px and 16px targets against a 24px minimum. Here the trail is
 * waited for before anything is measured.
 */
const TRAILS: Array<{ route: string; root: string; rootHref: string }> = [
  { route: "/okh/okh-0001", root: "Designs", rootHref: "/okh" },
  { route: "/facilities/okw-1", root: "Facilities", rootHref: "/facilities" },
  { route: "/facilities/new", root: "Facilities", rootHref: "/facilities" },
  { route: "/visualization/sol-1", root: "Match", rootHref: "/match" },
  {
    route: "/packages/demo/widget/1.0.0",
    root: "Packages",
    rootHref: "/packages",
  },
  {
    route: "/assets/11111111-1111-4111-8111-111111111111",
    root: "Assets",
    rootHref: "/assets",
  },
  { route: "/assets/new", root: "Assets", rootHref: "/assets" },
  {
    route: "/assets/11111111-1111-4111-8111-111111111111/triage",
    root: "Assets",
    rootHref: "/assets",
  },
];

/** WCAG 2.5.8 Target Size (Minimum), AA. */
const MIN_TARGET = 24;

for (const { route, root, rootHref } of TRAILS) {
  test(`breadcrumb on ${route}`, async ({ page }) => {
    await page.goto(route);
    const nav = page.getByRole("navigation", { name: "Breadcrumb" });
    // Waited for, not assumed. The trail renders with the data.
    await nav.waitFor({ state: "visible" });

    const rootLink = nav.getByRole("link", { name: root, exact: true });
    await expect(rootLink).toHaveAttribute("href", rootHref);

    // The leaf is the current page: not a link, and announced as current.
    await expect(nav.locator('[aria-current="page"]')).toHaveCount(1);
    await expect(nav.locator('[aria-current="page"]')).not.toHaveJSProperty(
      "tagName",
      "A",
    );

    // The nav is a flex container, which blockifies its children, so 2.5.8's
    // inline exception does not apply and the link owes the full 24px.
    const box = await rootLink.boundingBox();
    expect(
      box?.height ?? 0,
      `"${root}" on ${route} is ${box?.height}px tall, under the ${MIN_TARGET}px minimum`,
    ).toBeGreaterThanOrEqual(MIN_TARGET);

    // Reached by keyboard, with a visible focus indicator, and it navigates.
    let reached = false;
    for (let tab = 0; tab < 20 && !reached; tab++) {
      await page.keyboard.press("Tab");
      reached = await rootLink.evaluate((el) => el === document.activeElement);
    }
    expect(
      reached,
      `"${root}" on ${route} was not reachable within 20 Tabs`,
    ).toBe(true);
    const ring = await rootLink.evaluate(
      (el) => getComputedStyle(el).boxShadow,
    );
    expect(ring, `no visible focus indicator on "${root}" (${route})`).not.toBe(
      "none",
    );

    await page.keyboard.press("Enter");
    await expect.poll(() => page.url()).toContain(rootHref);
  });
}

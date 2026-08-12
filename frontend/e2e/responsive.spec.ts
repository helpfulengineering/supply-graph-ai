import { expect } from "@playwright/test";
import { test } from "./mock-api";
import { networkSpacesFixture } from "../src/test/fixtures";

/**
 * The responsive gate — the narrow-viewport analogue of themes.spec.ts.
 *
 * Every other lane runs at Desktop Chrome, so the app's behaviour below 640px
 * was asserted nowhere and drifted: /match scrolled sideways because a
 * <fieldset> carries `min-inline-size: min-content` in the UA stylesheet and
 * therefore refuses to shrink below its widest row. The page grew past the
 * viewport while the header and footer — honest 100%-width bars — stopped at
 * the screen edge, so the chrome read as narrower than the content.
 *
 * Two properties, both measured from the live layout rather than asserted
 * against a class name, so a fix that only moves the class around cannot pass:
 *
 *   1. Nothing overflows the viewport horizontally.
 *   2. Interactive controls meet WCAG 2.5.8 (AA) target size — 24x24 CSS px.
 *
 * WIDTHS is the point of the loop. The bug above survives at 412px (Pixel 7)
 * on fixture data and only shows at 360px, and a gate that passes by seven
 * pixels is not a gate — so the floor is asserted, not a comfortable phone.
 * 768px catches the other half: a layout that stacks correctly on a phone and
 * then breaks in the tablet range nobody looks at.
 */

/**
 * Routes with enough interactive surface for the properties to mean something.
 *
 * Every entry is asserted to answer 200 before it is measured. That is not
 * defensive padding: the first draft of this list named three routes that did
 * not answer — `/network` (the facilities view lives at `/facilities`),
 * `/create` (it is `/okh/new`), and `/packages`. All three "passed", because a
 * 404 page has nothing on it to overflow and no controls to undersize. A
 * layout gate that quietly measures the error page is worse than no gate, so a
 * typo in this list now fails loudly instead of reading green.
 *
 * The first two were mine. The third was not: `/packages` had a view, a menu
 * entry, e2e specs and a parity row, and `.gitignore`'s unanchored `packages/`
 * had kept `app/packages/` out of every clone. Two changes found the same
 * missing route from opposite ends within a day — this check because a layout
 * assertion passed on an error page, and the sitemap work because a menu entry
 * led nowhere. Neither would have found it alone.
 */
const ROUTES = [
  "/",
  "/okh",
  "/okh/okh-0001",
  "/okh/new",
  "/okh/generate",
  "/facilities",
  "/facilities/okw-1",
  "/match",
  "/rfq",
  "/settings",
  "/settings/keys",
  "/help",
  "/packages",
  "/solutions",
  "/icons",
  "/visualization/sol-1",
  "/assets",
  "/assets/11111111-1111-4111-8111-111111111111",
  // The densest control surface the app has: N components, each with a
  // condition segmented control and up to three tri-state groups.
  "/assets/11111111-1111-4111-8111-111111111111/triage",
  "/assets/salvage",
];

/** 360 is the practical Android floor; 768 is the tablet/`md:` boundary. */
const WIDTHS = [360, 768];

const SELECTOR =
  "a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=radio], [role=option], [role=tab], summary";

/** WCAG 2.5.8 Target Size (Minimum), AA. */
const MIN_TARGET = 24;

/**
 * The shared fixtures carry three facilities called things like "Laser Fab
 * Lab" in "Austin". Production carries 3,193, including "Eigenbaukombinat
 * Halle e.V." in "Valle de Chalco Solidaridad, Mexico" — and the overflow this
 * lane exists to catch is driven by the widest row, so on fixture data the bug
 * is simply absent and a green run means nothing.
 *
 * Rather than lengthen the shared fixtures (every other spec asserts against
 * those names), the stress case substitutes its own payload for the one route
 * that renders a long list. The property under test is "the layout survives
 * content longer than the viewport", which is what actually broke.
 */
const LONG_SPACES = {
  ...networkSpacesFixture,
  spaces: networkSpacesFixture.spaces.map((s, i) => ({
    ...s,
    name: `${s.name} — Eigenbaukombinat Halle e.V. Extended Campus ${i + 1}`,
    city: "Valle de Chalco Solidaridad",
    region: "Estado de Mexico",
    country: "MX",
  })),
};

/**
 * How long the app must stay idle before its layout is called final. Long
 * enough for a component that mounts on the previous query's data to mount and
 * start its own fetch, which is the gap that made two rounds necessary.
 */
const QUIET_MS = 400;

/**
 * Wait until the page has painted the thing worth measuring.
 *
 * Not `networkidle`: Playwright discourages it, and it hangs outright on a
 * page that issues no requests of its own — /help is generated entirely from
 * NAV_GROUPS and SHORTCUTS, never fetches, and so never produces the quiet
 * transition the wait is listening for. Both /help checks sat there for the
 * full 30s timeout. It is also armed by the navigation and never re-armed, so
 * a query fired after the document went quiet does not delay it at all, which
 * is precisely the case that matters here.
 *
 * Nor the main landmark alone, which is what this used to settle on. `#main`
 * is the frame, not the contents, and the audit ran against whatever was
 * inside it at that instant — usually a loading state, sometimes a section
 * that had not mounted yet. The lane read green because it was reporting on
 * its own wait: fourteen routes at two widths finished in six seconds, and
 * /okh/okh-0001 and /packages were each hiding two controls under the WCAG
 * minimum that appeared a beat after the measurement was taken.
 *
 * Three waits, because there are three ways for content to still be coming:
 *
 *   1. The landmark exists at all.
 *   2. No `LoadingState` is on screen. It is the single component behind every
 *      loading surface in the app and carries `data-loading` for this; it also
 *      covers the one source that is not a query, the lazily imported map.
 *   3. React Query is idle, and stays idle. Loading states only speak for the
 *      surfaces that render one — `ReleasesStrip` renders null until it knows
 *      whether the design has packages — so the fetch count is the signal with
 *      no blind spot. Idle is checked twice around a quiet window because the
 *      count legitimately returns to zero mid-load: /okh/okh-0001 fetches the
 *      design, renders it, and only then mounts the strip that fetches the
 *      packages. Stopping at the first zero measures the page between them.
 *
 * A route that fetches nothing clears all three immediately, so the static
 * pages settle as fast as they always did.
 */
async function settle(page: import("@playwright/test").Page) {
  await page.waitForLoadState("load");
  await page.locator("#main").waitFor({ state: "visible" });
  await expect(page.locator("[data-loading]")).toHaveCount(0);

  // `pending` until the provider stack mounts, so this cannot pass on an app
  // whose queries have not started — "not yet" and "already done" are
  // different answers and the attribute keeps them apart. See app/providers.tsx.
  const idle = page.locator('html[data-fetching="0"]');
  for (let round = 0; round < 2; round++) {
    // Attached, not the default `visible`: this is an attribute on the root
    // element, and whether <html> is visible is not a question with a useful
    // answer — asking it turns "the app is still fetching" into a 30s timeout
    // reporting that <html> never became visible, which sends you nowhere.
    await idle.waitFor({ state: "attached" });
    await page.waitForTimeout(QUIET_MS);
  }
  await expect(idle).toBeAttached();
  await expect(page.locator("[data-loading]")).toHaveCount(0);
}

/** Measure the two properties from the live layout of whatever is loaded. */
async function audit(page: import("@playwright/test").Page) {
  return page.evaluate(
    ({ selector, minTarget }) => {
      const doc = document.documentElement;
      const vw = doc.clientWidth;

      const overflowing: string[] = [];
      for (const el of Array.from(
        document.querySelectorAll<HTMLElement>("body *"),
      )) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        // An element may legitimately sit outside its own scroll container
        // (Leaflet tiles, a deliberately side-scrolling table). What must
        // not happen is the PAGE growing, so only unclipped overflow counts.
        let clipped = false;
        for (let p = el.parentElement; p; p = p.parentElement) {
          if (getComputedStyle(p).overflowX !== "visible") {
            clipped = true;
            break;
          }
        }
        if (clipped) continue;
        if (r.right > vw + 1 || r.left < -1) {
          overflowing.push(
            `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ""} [${Math.round(r.left)}..${Math.round(r.right)}] class="${String(el.className).slice(0, 80)}"`,
          );
        }
      }

      const undersized: string[] = [];
      for (const el of Array.from(
        document.querySelectorAll<HTMLElement>(selector),
      )) {
        let r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;

        // The target is the region that accepts the click, and for a
        // checkbox or radio that region is its label: clicking the text
        // toggles the control. A native checkbox renders at 13-16px and
        // cannot be resized without appearance-none and a hand-drawn
        // glyph, so measuring the input alone would demand a rewrite of
        // every checkbox in the app and buy nobody a larger target. The
        // row is what a thumb hits, so the row is what gets measured.
        if (
          el instanceof HTMLInputElement &&
          (el.type === "checkbox" || el.type === "radio")
        ) {
          const label =
            el.closest("label") ??
            (el.id
              ? document.querySelector<HTMLLabelElement>(
                  `label[for="${CSS.escape(el.id)}"]`,
                )
              : null);
          if (label) r = label.getBoundingClientRect();
        }

        if (r.width >= minTarget && r.height >= minTarget) continue;
        // Off-screen until focused: the skip link is sized by its :focus
        // rules, and the resting box measured here is not the target.
        if (el.classList.contains("sr-only")) continue;
        // 2.5.8's inline exception: a target rendered inside a sentence is
        // sized by the line-height of the surrounding text, and padding it
        // out would break the line box. Flex and grid blockify their
        // children, so a link that LOOKS inline but is a flex item is a
        // standalone target and does not qualify.
        const parent = el.parentElement;
        const parentDisplay = parent ? getComputedStyle(parent).display : "";
        const inFlow = !/flex|grid/.test(parentDisplay);
        const isInline = getComputedStyle(el).display.startsWith("inline");
        const hasSurroundingText =
          !!parent &&
          (parent.textContent ?? "").trim() !== (el.textContent ?? "").trim();
        if (isInline && inFlow && hasSurroundingText) continue;

        undersized.push(
          `${el.tagName.toLowerCase()} ${Math.round(r.width)}x${Math.round(r.height)} "${(el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 40)}"`,
        );
      }

      return {
        vw,
        scrollWidth: doc.scrollWidth,
        overflowing,
        undersized: [...new Set(undersized)],
      };
    },
    { selector: SELECTOR, minTarget: MIN_TARGET },
  );
}

/**
 * Soft, so one run reports every defect on the page. Hard assertions stop at
 * the first, which turns a layout sweep into one round trip per offender —
 * and hides the fact that several of them usually share a cause.
 */
function expectClean(result: Awaited<ReturnType<typeof audit>>) {
  expect
    .soft(
      result.overflowing,
      `elements overflow the ${result.vw}px viewport:\n${result.overflowing.join("\n")}`,
    )
    .toEqual([]);
  expect
    .soft(
      result.scrollWidth,
      `the document scrolls horizontally at ${result.vw}px`,
    )
    .toBeLessThanOrEqual(result.vw);
  expect
    .soft(
      result.undersized,
      `controls under the ${MIN_TARGET}x${MIN_TARGET} WCAG 2.5.8 minimum:\n${result.undersized.join("\n")}`,
    )
    .toEqual([]);
}

/**
 * The Settings routes are admin-only, and `RequireAdmin` sends everyone else to
 * `/`. Without a token this lane spent three of its fourteen routes measuring
 * the home page under three different names — /settings and /settings/keys
 * reported clean because they were never rendered. The token is the one
 * settings.spec.ts uses; the mocked whoami fixture makes it an admin.
 */
async function signIn(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });
}

for (const width of WIDTHS) {
  for (const route of ROUTES) {
    test(`${route} @${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      await signIn(page);
      const response = await page.goto(route);
      // See ROUTES: a 404 page passes every check below for the wrong reason.
      expect(
        response?.status(),
        `${route} did not answer 200 — the assertions below would measure the error page`,
      ).toBe(200);
      await settle(page);
      // And neither does the page it bounced you to. A 200 only says the route
      // exists; the app can still decide, client-side and after the fact, that
      // you may not see it. That is how /settings/keys came to be audited as a
      // second copy of the home page — silently, and for months.
      //
      // Landing deeper is not a bounce: /settings opens its default tab at
      // /settings/session, which is the section rendering itself. Landing
      // somewhere else entirely is, and `/` is checked exactly so that a route
      // that dumps you at the home page cannot claim to be a descendant of it.
      const landed = new URL(page.url()).pathname;
      expect(
        landed === route || landed.startsWith(`${route}/`),
        `${route} left you on ${landed} — the assertions below would measure that page instead`,
      ).toBe(true);
      expectClean(await audit(page));
    });
  }
}

test("/match survives production-length facility names @360px", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.route("**/api/okw/spaces*", (route) =>
    route.fulfill({ json: LONG_SPACES }),
  );
  await page.goto("/match");
  await settle(page);
  expectClean(await audit(page));
});

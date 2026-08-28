import { test, expect, type Page } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

/**
 * The dashboard's map sheet: what a pan raises, and where it paints.
 *
 * The paint-order test is why this file exists. The sheet shipped at `z-50`,
 * which reads as "above the page" and was not: the map card is `relative` with
 * `z-index: auto`, so it opens no stacking context, and Leaflet's own layers —
 * 400 for the tile and marker panes, 700 for popups, 800 and 1000 for the
 * controls — were compared against the sheet directly. It rose in front of the
 * page and behind the map it belongs to.
 *
 * Nothing in the DOM was wrong, which is the point, and two obvious ways of
 * catching it do not. `toBeVisible()` passes: Playwright's visibility is box,
 * opacity and `display`, and it never asks what is painted on top. A hit test
 * with `elementFromPoint` passes too — it answers which element takes a click,
 * and Leaflet's tile pane takes none, so the buried sheet won every sample.
 * What was wrong was the stacking, so the stacking is what is measured.
 */

const SHEET = 'aside[aria-label="Spaces in view"]';

/** Open the sheet the way a reader does: by dragging the map. */
async function panTheMap(page: Page): Promise<void> {
  const map = page.locator(".leaflet-container");
  await map.waitFor({ state: "visible" });
  const box = await map.boundingBox();
  if (!box) throw new Error("the map has no box to drag");
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x - 24, y - 12, { steps: 8 });
  await page.mouse.up();
}

/**
 * A network dense enough for the sheet to reach its cap.
 *
 * The shared fixture holds a handful of spaces, so the sheet opens 210px tall
 * and stops short of a 438px map — the two boxes never meet and a paint-order
 * test on them proves nothing. The bug was reported against 1,900 spaces, where
 * the sheet is at its 70svh ceiling and sits squarely over the map, so that is
 * the condition to reproduce.
 */
async function routeDenseNetwork(page: Page): Promise<void> {
  const spaces = Array.from({ length: 60 }, (_, i) => ({
    id: `urn:mak:space/dense-${i}`,
    name: `Dense Workshop ${i}`,
    lat: 45 + (i % 10) * 0.4,
    lon: 8 + Math.floor(i / 10) * 0.4,
    source: "mom",
    city: "Somewhere",
    region: null,
    country: "IT",
    status: "active",
    processes: ["cnc_machining"],
    access_type: null,
    url: "https://example.org",
    ambiguous: false,
  }));
  await page.route("**/api/okw/spaces*", (route) =>
    route.fulfill({
      json: {
        success: true,
        spaces,
        total: spaces.length,
        local_count: 0,
        mom_count: spaces.length,
        dropped_no_coords: 0,
        mom_available: true,
      },
    }),
  );
}

/**
 * Wait for the slide to finish, by the destination rather than by the
 * animation. `getAnimations()` is empty both after a transition ends and
 * before it starts, so waiting on it raced the open and measured a sheet still
 * parked off-screen. Flush with the bottom edge is where it is going, and it is
 * only ever there when it has arrived.
 */
async function settleSheet(page: Page): Promise<void> {
  await expect
    .poll(async () => {
      const box = await page.locator(SHEET).boundingBox();
      const height = page.viewportSize()?.height ?? 0;
      return box ? Math.round(box.y + box.height) === height : false;
    })
    .toBe(true);
}

/**
 * Where the sheet sits in the paint order relative to the map's own layers.
 *
 * Not `elementFromPoint`. That was the first attempt and it passed on the bug:
 * a hit test answers which element takes a click, and Leaflet's tile pane does
 * not take clicks — so the buried sheet "won" every sample while the tiles were
 * painted over it. Stacking is the property that was wrong, so stacking is what
 * gets measured.
 */
async function stackingVerdict(page: Page): Promise<{
  mapIsolated: boolean;
  sheetZ: number;
  rivals: { cls: string; z: number }[];
}> {
  return page.evaluate((selector) => {
    const zOf = (el: Element): number | null => {
      const v = getComputedStyle(el).zIndex;
      return v === "auto" ? null : Number(v);
    };
    // If any ancestor of the map opened a stacking context, the map's insides
    // are sealed inside it and cannot outrank the sheet whatever they claim.
    const opensContext = (el: Element): boolean => {
      const cs = getComputedStyle(el);
      return (
        cs.transform !== "none" ||
        cs.filter !== "none" ||
        cs.backdropFilter !== "none" ||
        cs.isolation === "isolate" ||
        Number(cs.opacity) < 1 ||
        cs.contain.includes("paint") ||
        (cs.position !== "static" && cs.zIndex !== "auto")
      );
    };
    const map = document.querySelector(".leaflet-container");
    let node = map?.parentElement ?? null;
    let mapIsolated = false;
    while (node && node !== document.body) {
      if (opensContext(node)) {
        mapIsolated = true;
        break;
      }
      node = node.parentElement;
    }
    const sheet = document.querySelector(selector);
    const rivals = [
      ...document.querySelectorAll(
        ".leaflet-pane, .leaflet-control, .leaflet-top, .leaflet-bottom",
      ),
    ]
      .map((el) => ({ cls: el.className.toString(), z: zOf(el) }))
      .filter((r): r is { cls: string; z: number } => r.z !== null);
    return { mapIsolated, sheetZ: sheet ? (zOf(sheet) ?? 0) : 0, rivals };
  }, SHEET);
}

test("the dashboard map draws no sheet until it is touched", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator(".leaflet-container").waitFor({ state: "visible" });

  // Present in the DOM and parked off-screen, so nothing about it is reachable
  // — a surface that opened itself on load is a surface nobody asked for.
  const sheet = page.locator(SHEET);
  await expect(sheet).toHaveAttribute("aria-hidden", "true");
  await expect(sheet).not.toContainText(/in view/);
});

test("a gesture at the map raises the sheet of what it frames", async ({
  page,
}) => {
  await page.goto("/");
  await panTheMap(page);

  const sheet = page.locator(SHEET);
  await expect(sheet).toHaveAttribute("aria-hidden", "false");
  await expect(
    sheet.getByRole("heading", { name: /in view|nothing in view/i }),
  ).toBeVisible();
});

test("the open sheet paints above the map, not under it @390px", async ({
  page,
}) => {
  // A phone, deliberately. At 1280x800 the map ends well above the sheet, so
  // the two boxes never meet and the hit test passes on a broken z-index —
  // this test was written at desktop first and proved nothing. The overlap is
  // asserted below rather than assumed, so it cannot quietly stop meeting
  // again.
  await page.setViewportSize({ width: 390, height: 844 });
  await routeDenseNetwork(page);
  await page.goto("/");
  await panTheMap(page);

  const sheet = page.locator(SHEET);
  await expect(sheet).toHaveAttribute("aria-hidden", "false");
  await settleSheet(page);

  const box = await sheet.boundingBox();
  const mapBox = await page.locator(".leaflet-container").boundingBox();
  expect(box, "the open sheet has no box").not.toBeNull();
  expect(mapBox, "the map has no box").not.toBeNull();
  if (!box || !mapBox) return;
  expect(
    box.y < mapBox.y + mapBox.height && mapBox.y < box.y + box.height,
    `the sheet and the map do not overlap — this test would prove nothing (sheet ${JSON.stringify(box)}, map ${JSON.stringify(mapBox)})`,
  ).toBe(true);

  const { mapIsolated, sheetZ, rivals } = await stackingVerdict(page);
  const highest = rivals.reduce((worst, r) => (r.z > worst.z ? r : worst), {
    cls: "none",
    z: 0,
  });
  expect(
    mapIsolated || sheetZ > highest.z,
    `the map paints over its own sheet: sheet z-index ${sheetZ}, "${highest.cls}" at ${highest.z}, and nothing between them opens a stacking context`,
  ).toBe(true);
});

test("the sheet is full-bleed and flush to the bottom edge @390px", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await panTheMap(page);

  const sheet = page.locator(SHEET);
  await expect(sheet).toHaveAttribute("aria-hidden", "false");
  await settleSheet(page);

  const box = await sheet.boundingBox();
  if (!box) throw new Error("the open sheet has no box");
  expect(Math.round(box.x), "not flush to the left edge").toBe(0);
  expect(Math.round(box.width), "not full-bleed").toBe(390);
  expect(Math.round(box.y + box.height), "not flush to the bottom").toBe(844);
  // 70svh, so the map it describes is never entirely hidden behind it.
  expect(box.height).toBeLessThanOrEqual(844 * 0.7 + 1);
});

test("the open sheet is clean under axe", async ({ page }) => {
  await page.goto("/");
  await panTheMap(page);
  await expect(page.locator(SHEET)).toHaveAttribute("aria-hidden", "false");
  await expectNoA11yViolations(page);
});

test("the sheet closes on Escape and on its button, and traps nothing", async ({
  page,
}) => {
  await page.goto("/");
  await panTheMap(page);
  const sheet = page.locator(SHEET);
  await expect(sheet).toHaveAttribute("aria-hidden", "false");

  // It is not a modal: it opened on a gesture made for another reason, so it
  // must not claim the page or move the focus out from under the reader.
  await expect(sheet).not.toHaveAttribute("aria-modal", "true");
  expect(
    await page.evaluate(
      (selector) =>
        !!document.querySelector(selector)?.contains(document.activeElement),
      SHEET,
    ),
    "the sheet stole focus on open",
  ).toBe(false);

  await sheet.getByRole("button", { name: "Close" }).click();
  await expect(sheet).toHaveAttribute("aria-hidden", "true");

  await panTheMap(page);
  await expect(sheet).toHaveAttribute("aria-hidden", "false");
  await page.keyboard.press("Escape");
  await expect(sheet).toHaveAttribute("aria-hidden", "true");
});

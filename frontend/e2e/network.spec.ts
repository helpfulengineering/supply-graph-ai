import { test, expect } from "./mock-api";

// Issue #230: the unified network surface at /facilities (local OKW ∪ MoM),
// with server-side filters and list/map views.

test("network surface loads", async ({ page }) => {
  await page.goto("/facilities");
  await expect(
    page.getByRole("heading", { name: "Network", level: 1 }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: /filters/i })).toBeVisible();
});

test("lists spaces from both sources with badges (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/facilities");
  await expect(
    page.getByRole("heading", { name: "Laser Fab Lab" }),
  ).toBeVisible();
  // A Maps of Making space is included in the same list.
  await expect(
    page.getByRole("heading", { name: "FabLab Lazio Roma" }),
  ).toBeVisible();
  // The source Badge itself, not any text that happens to say it: this used to
  // match a sentence of page copy, so removing that copy sent .first() to the
  // hidden <option> in the source filter and the test failed for a reason that
  // had nothing to do with badges.
  await expect(
    page
      .locator("span.rounded-full")
      .filter({ hasText: "Maps of Making" })
      .first(),
  ).toBeVisible();
});

test("toggling to the map view renders the map (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/facilities");
  // The toggle is a radio group, not a group of toggle buttons: it is a
  // one-of-N choice, and SegmentedControl gives it the radio semantics and the
  // arrow-key handling the hand-rolled version promised but never had.
  await page.getByRole("radio", { name: "Map" }).click();
  await expect(page.locator(".leaflet-container")).toBeVisible();
});

test("applying a filter sends it to the server (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "inspects the request");
  const urls: string[] = [];
  await page.route("**/v1/api/okw/spaces**", async (route) => {
    urls.push(route.request().url());
    await route.continue();
  });
  await page.goto("/facilities");
  await page.getByLabel("Source").selectOption("mom");
  // A new request carrying the source filter is issued (server-side filtering).
  await expect
    .poll(() => urls.some((u) => u.includes("source=mom")))
    .toBeTruthy();
});

test("flags ambiguous spaces under a local-only filter (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name === "real-api",
    "forces an ambiguous response",
  );
  await page.route("**/v1/api/okw/spaces**", (route) =>
    route.fulfill({
      json: {
        success: true,
        spaces: [
          {
            id: "urn:m",
            name: "Ambiguous MoM",
            lat: 1,
            lon: 2,
            source: "mom",
            city: "Rome",
            region: null,
            country: "IT",
            status: "active",
            processes: [],
            access_type: null,
            url: "https://m",
            ambiguous: true,
          },
        ],
        total: 1,
        local_count: 0,
        mom_count: 1,
        dropped_no_coords: 0,
        mom_available: true,
      },
    }),
  );
  await page.goto("/facilities");
  await expect(
    page.getByText(/ambiguous for the current filter/i),
  ).toBeVisible();
});

test("shows the empty state (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an empty response");
  await page.route("**/v1/api/okw/spaces**", (route) =>
    route.fulfill({
      json: {
        success: true,
        spaces: [],
        total: 0,
        local_count: 0,
        mom_count: 0,
        dropped_no_coords: 0,
        mom_available: true,
      },
    }),
  );
  await page.goto("/facilities");
  await expect(page.getByText("No spaces yet")).toBeVisible();
  // Header and empty-state both expose the same soft-gate CTA.
  await expect(
    page.getByRole("button", { name: /New facility|Connect API key/i }).first(),
  ).toBeVisible();
});

test("hands the active filter off to the match flow", async ({ page }) => {
  await page.goto("/facilities");
  await page.getByLabel("Source").selectOption("mom");
  await page
    .getByRole("button", { name: /match a design against these/i })
    .click();
  await expect(page).toHaveURL(/\/match\?.*network=1/);
  await expect(page).toHaveURL(/source=mom/);
  // The match view enters network mode.
  await expect(page.getByText(/matching against the network/i)).toBeVisible();
});

test("shows the error state with retry (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an error");
  await page.route("**/v1/api/okw/spaces**", (route) =>
    route.fulfill({ status: 500, json: { detail: "boom" } }),
  );
  await page.goto("/facilities");
  await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
});

test("search by name narrows the network (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/facilities");

  const search = page.getByLabel("Search by name");
  await expect(search).toBeVisible();

  // Establish a baseline, then confirm the query actually narrows it.
  const before = await page.getByRole("heading", { level: 3 }).count();
  await search.fill("zzz-no-such-workshop");
  await expect
    .poll(async () => page.getByRole("heading", { level: 3 }).count())
    .toBeLessThan(Math.max(before, 1));
});

import { test, expect } from "./mock-api";

// Issue #230: the unified network surface at /facilities (local OKW ∪ MoM),
// with server-side filters and list/map views.

test("network surface loads", async ({ page }) => {
  await page.goto("/facilities");
  await expect(page.getByRole("heading", { name: "Network", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: /filters/i })).toBeVisible();
});

test("lists spaces from both sources with badges (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/facilities");
  await expect(page.getByRole("heading", { name: "Laser Fab Lab" })).toBeVisible();
  // A Maps of Making space is included in the same list.
  await expect(page.getByRole("heading", { name: "FabLab Lazio Roma" })).toBeVisible();
  await expect(page.getByText("Maps of Making").first()).toBeVisible();
});

test("toggling to the map view renders the map (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/facilities");
  await page.getByRole("button", { name: "map" }).click();
  await expect(page.locator(".leaflet-container")).toBeVisible();
});

test("applying a filter sends it to the server (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "inspects the request");
  const urls: string[] = [];
  await page.route("**/v1/api/okw/spaces**", async (route) => {
    urls.push(route.request().url());
    await route.continue();
  });
  await page.goto("/facilities");
  await page.getByLabel("Source").selectOption("mom");
  // A new request carrying the source filter is issued (server-side filtering).
  await expect.poll(() => urls.some((u) => u.includes("source=mom"))).toBeTruthy();
});

test("flags ambiguous spaces under a local-only filter (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an ambiguous response");
  await page.route("**/v1/api/okw/spaces**", (route) =>
    route.fulfill({
      json: {
        success: true,
        spaces: [
          { id: "urn:m", name: "Ambiguous MoM", lat: 1, lon: 2, source: "mom", city: "Rome",
            region: null, country: "IT", status: "active", processes: [], access_type: null,
            url: "https://m", ambiguous: true },
        ],
        total: 1, local_count: 0, mom_count: 1, dropped_no_coords: 0, mom_available: true,
      },
    }),
  );
  await page.goto("/facilities");
  await expect(page.getByText(/ambiguous for the current filter/i)).toBeVisible();
});

test("shows the empty state (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an empty response");
  await page.route("**/v1/api/okw/spaces**", (route) =>
    route.fulfill({
      json: { success: true, spaces: [], total: 0, local_count: 0, mom_count: 0, dropped_no_coords: 0, mom_available: true },
    }),
  );
  await page.goto("/facilities");
  await expect(page.getByText("No spaces are available yet.")).toBeVisible();
});

test("shows the error state with retry (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an error");
  await page.route("**/v1/api/okw/spaces**", (route) =>
    route.fulfill({ status: 500, json: { detail: "boom" } }),
  );
  await page.goto("/facilities");
  await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
});

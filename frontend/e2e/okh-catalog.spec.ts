import { test, expect } from "./mock-api";
import { okhListEmptyFixture } from "../src/test/fixtures";

// Slice A1: faceted OKH design catalog. Mocked lane (default gate) covers the
// facet behavior; the real-api lane only runs the lenient "loads" check.

test("faceted catalog loads with a filter panel", async ({ page }) => {
  await page.goto("/okh");
  await expect(
    page.getByRole("heading", { name: /open hardware designs/i }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Filters" })).toBeVisible();
});

test("shows fixture designs (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/okh");
  await expect(page.getByRole("heading", { name: "Open Ventilator" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Face Shield" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Test Rig" })).toBeVisible();
});

test("selecting a facet narrows the results (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/okh");
  // Only Face Shield is GPL-2.0.
  await page.getByRole("checkbox", { name: /GPL-2\.0/ }).check();
  await expect(page.getByRole("heading", { name: "Face Shield" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Open Ventilator" })).toBeHidden();
  // Facet selection is reflected in the URL (deep-linkable).
  await expect(page).toHaveURL(/license=GPL-2\.0/);
});

test("category facet is the primary spine and narrows results (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/okh");
  // Wait for the list (and thus the derived facets) to settle before touching a
  // facet — otherwise the facet checkboxes can remount mid-click when the OKH
  // query resolves, dropping the check.
  await expect(page.getByRole("heading", { name: "Open Ventilator" })).toBeVisible();
  // Category is present as a facet group. Test Rig ("Calibration test rig") is
  // the only Test & Measurement device.
  await expect(page.getByRole("heading", { name: "Category" })).toBeVisible();
  // Retry until the check sticks: the facet can still remount as counts recompute,
  // which otherwise drops the click ("did not change its state").
  await expect(async () => {
    await page.getByRole("checkbox", { name: /Test & Measurement/ }).check();
    await expect(page).toHaveURL(/category=Test/);
  }).toPass();
  await expect(page.getByRole("heading", { name: "Test Rig" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Open Ventilator" })).toBeHidden();
  await expect(page).toHaveURL(/category=Test/);
});

test("shows the empty state (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an empty response");
  await page.route("**/v1/api/okh**", (route) =>
    route.fulfill({ json: okhListEmptyFixture }),
  );
  await page.goto("/okh");
  await expect(page.getByText(/no designs/i)).toBeVisible();
});

test("shows the error state with retry (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an error response");
  await page.route("**/v1/api/okh**", (route) =>
    route.fulfill({ status: 503, json: { message: "boom" } }),
  );
  await page.goto("/okh");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
});

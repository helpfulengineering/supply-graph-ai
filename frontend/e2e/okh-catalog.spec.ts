import { test, expect } from "./mock-api";
import { okhListEmptyFixture } from "../src/test/fixtures";

// Slice 1: OKH design catalog list. Runs in the mocked lane (default gate) and,
// for the lenient "loads" check, the real-api lane.

test("OKH catalog route loads", async ({ page }) => {
  await page.goto("/okh");
  await expect(
    page.getByRole("heading", { name: /open hardware designs/i }),
  ).toBeVisible();
});

test("OKH catalog shows fixture designs (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/okh");
  await expect(page.getByRole("heading", { name: "Open Ventilator" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Face Shield" })).toBeVisible();
});

test("OKH catalog shows the empty state (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an empty response");
  await page.route("**/v1/api/okh**", (route) =>
    route.fulfill({ json: okhListEmptyFixture }),
  );
  await page.goto("/okh");
  await expect(page.getByText(/no designs/i)).toBeVisible();
});

test("OKH catalog shows the error state with retry (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an error response");
  await page.route("**/v1/api/okh**", (route) =>
    route.fulfill({ status: 503, json: { message: "boom" } }),
  );
  await page.goto("/okh");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
});

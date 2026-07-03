import { test, expect } from "./mock-api";
import { okwSearchEmptyFixture } from "../src/test/fixtures";

// Slice #188: read-only OKW facility catalog. Mocked lane covers the behavior;
// the real-api lane runs the lenient "loads" check against the live corpus.

test("facility catalog loads", async ({ page }) => {
  await page.goto("/facilities");
  await expect(
    page.getByRole("heading", { name: /manufacturing facilities/i }),
  ).toBeVisible();
});

test("shows fixture facilities with humanized processes (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/facilities");
  await expect(page.getByRole("heading", { name: "Laser Fab Lab" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Community Makerspace" })).toBeVisible();
  // Wikipedia URI is humanized for display.
  await expect(page.getByText("Laser Cutter")).toBeVisible();
});

test("filtering by access type narrows results (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/facilities");
  await page.getByRole("button", { name: "Public", pressed: false }).click();
  await expect(page.getByRole("heading", { name: "Community Makerspace" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Laser Fab Lab" })).toBeHidden();
});

test("shows the empty state (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an empty response");
  await page.route("**/v1/api/okw/search**", (route) =>
    route.fulfill({ json: okwSearchEmptyFixture }),
  );
  await page.goto("/facilities");
  await expect(page.getByText(/no facilities/i)).toBeVisible();
});

test("shows the error state with retry (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an error response");
  await page.route("**/v1/api/okw/search**", (route) =>
    route.fulfill({ status: 500, json: { message: "boom" } }),
  );
  await page.goto("/facilities");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
});

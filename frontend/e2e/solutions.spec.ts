import { test, expect } from "./mock-api";
import { solutionsEmptyFixture } from "../src/test/fixtures";

// Slice #195: saved solutions list + load (into the supply-tree explorer).

test("solutions page loads", async ({ page }) => {
  await page.goto("/solutions");
  await expect(page.getByRole("heading", { name: /saved solutions/i })).toBeVisible();
});

test("lists saved solutions and loads one into the explorer (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/solutions");
  await expect(page.getByRole("heading", { name: "Open Ventilator" })).toBeVisible();
  await expect(page.getByText("95%")).toBeVisible();
  // Loading a solution navigates into the supply-tree explorer.
  await page.getByRole("link", { name: /open ventilator/i }).click();
  await expect(page).toHaveURL(/\/visualization\/sol-1/);
  await expect(page.getByRole("heading", { name: "Supply Tree", level: 1 })).toBeVisible();
});

test("shows the empty state when there are no solutions (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an empty response");
  await page.route("**/v1/api/supply-tree/solutions**", (route) =>
    route.fulfill({ json: solutionsEmptyFixture }),
  );
  await page.goto("/solutions");
  await expect(page.getByText(/no saved solutions/i)).toBeVisible();
});

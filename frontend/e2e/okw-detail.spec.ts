import { test, expect } from "./mock-api";

// Slice #189: OKW facility detail + validate. Mocked lane (fixture id okw-1).

test("shows OKW facility detail (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses a fixture id");
  await page.goto("/facilities/okw-1");
  await expect(page.getByRole("heading", { name: "Laser Fab Lab" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /equipment/i })).toBeVisible();
  // Equipment type Wikipedia URI is humanized.
  await expect(page.getByText("Laser Cutter")).toBeVisible();
});

test("validate surfaces a validation result (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses fixtures");
  await page.goto("/facilities/okw-1");
  await page.getByRole("button", { name: "Validate" }).click();
  await expect(page.getByRole("heading", { name: "Validation" })).toBeVisible();
  await expect(page.getByText(/Missing intended_use/)).toBeVisible();
});

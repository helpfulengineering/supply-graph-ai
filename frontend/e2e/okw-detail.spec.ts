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

test("lists the designs the facility can make and links to them (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/facilities/okw-1");
  await expect(
    page.getByRole("heading", { name: /designs this facility can make/i }),
  ).toBeVisible();
  // Reverse-match result links into the design detail.
  const link = page.getByRole("link", { name: /open ventilator/i });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(/\/okh\/okh-0001/);
});

test("validate surfaces a validation result (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses fixtures");
  await page.goto("/facilities/okw-1");
  await page.getByRole("button", { name: "Validate" }).click();
  await expect(page.getByRole("heading", { name: "Validation" })).toBeVisible();
  await expect(page.getByText(/Missing intended_use/)).toBeVisible();
});

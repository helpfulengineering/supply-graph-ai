import { test, expect } from "./mock-api";

// Slice 2 (#187): OKH design detail + validate. Mocked lane (the fixture id
// okh-0001 isn't guaranteed in the live corpus).

test("shows OKH design detail (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses a fixture id");
  await page.goto("/okh/okh-0001");
  await expect(page.getByRole("heading", { name: "Open Ventilator" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Design Info" })).toBeVisible();
});

test("validate surfaces a validation result (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses fixtures");
  await page.goto("/okh/okh-0001");
  await page.getByRole("button", { name: "Validate" }).click();
  await expect(page.getByRole("heading", { name: "Validation" })).toBeVisible();
  await expect(page.getByText(/Missing intended_use/)).toBeVisible();
  await expect(page.getByText(/Add a bill of materials/)).toBeVisible();
});

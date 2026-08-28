import { test, expect } from "./mock-api";

// Slice 2 (#187): OKH design detail + validate. Mocked lane (the fixture id
// okh-0001 isn't guaranteed in the live corpus).

test("shows OKH design detail (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses a fixture id");
  await page.goto("/okh/okh-0001");
  await expect(
    page.getByRole("heading", { name: "Open Ventilator" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Design Info" }),
  ).toBeVisible();
});

test("validate surfaces a validation result (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses fixtures");
  await page.goto("/okh/okh-0001");
  await page.getByRole("button", { name: "Validate" }).click();
  await expect(page.getByRole("heading", { name: "Validation" })).toBeVisible();
  await expect(page.getByText(/Missing intended_use/)).toBeVisible();
  await expect(page.getByText(/Add a bill of materials/)).toBeVisible();
});

test("requirements disclosure says what matching will look for", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses fixture ids");
  await page.goto("/okh/okh-0001");

  // Closed by default: extraction POSTs the whole manifest for a panel most
  // readers will not open.
  await expect(page.getByText("3d_printing")).toHaveCount(0);

  await page
    .getByRole("button", { name: "What will matching look for?" })
    .click();
  await expect(page.getByText("3d_printing")).toBeVisible();
});

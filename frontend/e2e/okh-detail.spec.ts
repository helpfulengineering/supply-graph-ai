import { test, expect } from "./mock-api";

// Slice 2 (#187): OKH design detail + validate. Mocked lane (the fixture id
// okh-0001 isn't guaranteed in the live corpus).

test("shows OKH design detail (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses a fixture id");
  await page.goto("/okh/okh-0001");
  await expect(page.getByRole("heading", { name: "Open Ventilator" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Design Info" })).toBeVisible();
  // Intended Use moved up (rendered near Design Info).
  await expect(page.getByRole("heading", { name: "Intended Use" })).toBeVisible();
});

test("files view: headline default + file-tree toggle (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses fixture files");
  await page.goto("/okh/okh-0001");
  // Headline mode surfaces the README (not every raw file).
  await expect(page.getByText("README.md")).toBeVisible();
  // Toggle to the file tree → directory folders appear.
  await page.getByRole("button", { name: "File tree" }).click();
  await expect(page.getByRole("button", { name: /docs/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /images/ })).toBeVisible();
});

test("validate surfaces a validation result (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses fixtures");
  await page.goto("/okh/okh-0001");
  await page.getByRole("button", { name: "Validate" }).click();
  await expect(page.getByRole("heading", { name: "Validation" })).toBeVisible();
  await expect(page.getByText(/Missing intended_use/)).toBeVisible();
  await expect(page.getByText(/Add a bill of materials/)).toBeVisible();
});

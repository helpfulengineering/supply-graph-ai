import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

test("create design page renders", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked lane");
  await page.goto("/okh/new");
  await expect(page.getByRole("heading", { name: "New design" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create" })).toBeVisible();
  await expectNoA11yViolations(page);
});

test("create facility page renders", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked lane");
  await page.goto("/facilities/new");
  await expect(page.getByRole("heading", { name: "New facility" })).toBeVisible();
  await expect(page.getByLabel("Name *")).toBeVisible();
  await expect(page.getByRole("button", { name: "Create facility" })).toBeVisible();
  await expect(page.getByLabel("3D Printing")).toBeVisible();
  await expectNoA11yViolations(page);
});

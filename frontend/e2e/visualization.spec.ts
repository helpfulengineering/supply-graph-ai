import { test, expect } from "./mock-api";

// Slice #193: supply-tree explorer. Mocked lane (fixture solution sol-1).

test("supply-tree explorer renders KPIs and the tree (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses a fixture solution id");
  await page.goto("/visualization/sol-1");
  await expect(page.getByRole("heading", { name: "Supply Tree", level: 1 })).toBeVisible();
  // Facility distribution chart section (KPI derivation is unit-tested).
  await expect(page.getByText(/facility distribution/i)).toBeVisible();
});

test("shows production sequence and dependencies (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses a fixture solution id");
  await page.goto("/visualization/sol-1");
  await expect(page.getByRole("heading", { name: /production sequence/i })).toBeVisible();
  // Dependency line: "Frame depends on Base Plate" (unique to the deps section).
  await expect(page.getByText(/depends on/i)).toBeVisible();
});

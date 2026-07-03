import { test, expect } from "./mock-api";

// Slice #191: run a match + ranked results. Mocked lane (deterministic match).

test("match page loads with a design selector", async ({ page }) => {
  await page.goto("/match");
  await expect(page.getByRole("heading", { name: /match a design/i })).toBeVisible();
  await expect(page.getByLabel("Design to match")).toBeVisible();
});

test("running a match shows ranked results, summary, and coverage gaps (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/match");
  await page.getByLabel("Design to match").selectOption({ label: "Open Ventilator" });
  await page.getByRole("button", { name: /run match/i }).click();

  // Ranked results (top solution first) with a confidence badge.
  await expect(page.getByRole("heading", { name: "FabLab Drome" })).toBeVisible();
  await expect(page.getByText(/High · 95%/)).toBeVisible();
  // Plain-language summary + coverage gaps.
  await expect(page.getByText(/2 candidate solutions found/)).toBeVisible();
  await expect(page.getByText(/CNC Machining/)).toBeVisible();
  // Hand-off link into the supply-tree explorer.
  await expect(page.getByRole("link", { name: /view supply tree/i }).first()).toBeVisible();
});

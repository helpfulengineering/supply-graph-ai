import { test, expect } from "./mock-api";
import { matchResponseFixture } from "../src/test/fixtures";

// Slice #191/#192: run a match + ranked results + System Mode. Mocked lane.

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

test("System Mode selector controls the match request (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "inspects the request body");
  let body: { quality_level?: string; strict_mode?: boolean } | null = null;
  await page.route("**/v1/api/match", async (route) => {
    body = route.request().postDataJSON();
    await route.fulfill({ json: matchResponseFixture });
  });

  await page.goto("/match");
  await page.getByLabel("Design to match").selectOption({ label: "Open Ventilator" });
  await page.getByRole("radio", { name: "Strict" }).click();
  await page.getByRole("button", { name: /run match/i }).click();

  await expect(page.getByRole("heading", { name: "FabLab Drome" })).toBeVisible();
  // Strict mode maps to medical quality + strict validation.
  expect(body!.quality_level).toBe("medical");
  expect(body!.strict_mode).toBe(true);
});

test("selecting a facility subset sends okw_ids in the match request (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "inspects the request body");
  let body: { okw_ids?: string[] } | null = null;
  await page.route("**/v1/api/match", async (route) => {
    body = route.request().postDataJSON();
    await route.fulfill({ json: matchResponseFixture });
  });

  await page.goto("/match");
  await page.getByLabel("Design to match").selectOption({ label: "Open Ventilator" });

  // Narrow matching to a single facility via the optional facility filter.
  await page.getByRole("button", { name: /facilities/i }).click();
  await page.getByLabel("Laser Fab Lab").check();
  await expect(page.getByText(/limited to 1 facility/i)).toBeVisible();

  await page.getByRole("button", { name: /run match/i }).click();
  await expect(page.getByRole("heading", { name: "FabLab Drome" })).toBeVisible();
  expect(body!.okw_ids).toEqual(["okw-1"]);
});

test("with no facility subset the request omits okw_ids (matches all, mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "inspects the request body");
  let body: Record<string, unknown> | null = null;
  await page.route("**/v1/api/match", async (route) => {
    body = route.request().postDataJSON();
    await route.fulfill({ json: matchResponseFixture });
  });

  await page.goto("/match");
  await page.getByLabel("Design to match").selectOption({ label: "Open Ventilator" });
  await page.getByRole("button", { name: /run match/i }).click();

  await expect(page.getByRole("heading", { name: "FabLab Drome" })).toBeVisible();
  expect(body).not.toHaveProperty("okw_ids");
});

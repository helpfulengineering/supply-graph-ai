import { test, expect } from "./mock-api";
import { matchResponseFixture } from "../src/test/fixtures";

// Slice #191/#192: run a match + ranked results + System Mode. Mocked lane.

test("match page loads with design search and expanded facility filters", async ({ page }) => {
  await page.goto("/match");
  await expect(page.getByRole("heading", { name: /match a design/i })).toBeVisible();
  await expect(page.getByLabel("Search designs")).toBeVisible();
  await expect(page.getByLabel("Source")).toBeVisible();
  await expect(page.getByLabel("Country")).toBeVisible();
  await expect(page.getByLabel("State / Region")).toBeVisible();
  await expect(page.getByLabel("City")).toBeVisible();
});

test("running a match shows ranked results, summary, and coverage gaps (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/match");
  await page.getByLabel("Search designs").fill("Ventilator");
  await page.getByRole("option", { name: /Open Ventilator/i }).click();
  await page.getByLabel("Laser Fab Lab").check();
  await page.getByRole("button", { name: /run match/i }).click();

  await expect(page.getByRole("heading", { name: "FabLab Drome" })).toBeVisible();
  await expect(page.getByText(/High · 95%/)).toBeVisible();
  await expect(page.getByText(/2 candidate solutions found/)).toBeVisible();
  await expect(page.getByText(/CNC Machining/)).toBeVisible();
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
  await page.getByLabel("Search designs").fill("Ventilator");
  await page.getByRole("option", { name: /Open Ventilator/i }).click();
  await page.getByLabel("Laser Fab Lab").check();
  await page.getByRole("radio", { name: "Strict" }).click();
  await page.getByRole("button", { name: /run match/i }).click();

  await expect(page.getByRole("heading", { name: "FabLab Drome" })).toBeVisible();
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
  await page.getByLabel("Search designs").fill("Ventilator");
  await page.getByRole("option", { name: /Open Ventilator/i }).click();
  await page.getByLabel("Laser Fab Lab").check();
  await expect(page.getByText(/1 facility selected/i)).toBeVisible();

  await page.getByRole("button", { name: /run match/i }).click();
  await expect(page.getByRole("heading", { name: "FabLab Drome" })).toBeVisible();
  expect(body!.okw_ids).toEqual(["okw-1"]);
});

test("Run Match stays disabled until a facility is selected (mocked)", async ({ page }) => {
  await page.goto("/match");
  await page.getByLabel("Search designs").fill("Ventilator");
  await page.getByRole("option", { name: /Open Ventilator/i }).click();
  await expect(page.getByRole("button", { name: /run match/i })).toBeDisabled();
  await expect(page.getByText(/select at least one facility/i)).toBeVisible();
});

test("okw_id query prefills facility selection without autorunning (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "inspects the request body");
  let matchCalls = 0;
  await page.route("**/v1/api/match", async (route) => {
    matchCalls += 1;
    await route.fulfill({ json: matchResponseFixture });
  });

  await page.goto("/match?okw_id=okw-1");
  await expect(page.getByLabel("Laser Fab Lab")).toBeChecked();
  await expect.poll(() => matchCalls).toBe(0);
});

test("Maps of Making source shows MoM facilities (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/match");
  await page.getByLabel("Source").selectOption("mom");
  await expect(page.getByLabel("FabLab Lazio Roma")).toBeVisible();
  await expect(page.getByLabel("Laser Fab Lab")).toHaveCount(0);
});

test("network mode sends network_filter and shows the banner (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "inspects the request body");
  let body: { network_filter?: Record<string, unknown> } | null = null;
  await page.route("**/v1/api/match", async (route) => {
    body = route.request().postDataJSON();
    await route.fulfill({ json: matchResponseFixture });
  });

  await page.goto("/match?network=1&country=FR&process=laser_cutting");
  await expect(page.getByText(/matching against the network/i)).toBeVisible();
  await expect(page.getByText(/country: FR/)).toBeVisible();

  await page.getByLabel("Search designs").fill("Ventilator");
  await page.getByRole("option", { name: /Open Ventilator/i }).click();
  await page.getByRole("button", { name: /run match/i }).click();

  await expect(page.getByRole("heading", { name: "FabLab Drome" })).toBeVisible();
  expect(body!.network_filter).toMatchObject({ country: "FR", process: "laser_cutting", include_mom: true });
});

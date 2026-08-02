import { test, expect } from "./mock-api";
import { matchResponseFixture } from "../src/test/fixtures";

// Slice #191/#192: run a match + ranked results + System Mode. Mocked lane.

test("match page loads with design search and expanded facility filters", async ({
  page,
}, testInfo) => {
  // Real API with an empty catalog can omit the design search combobox.
  test.skip(testInfo.project.name === "real-api", "expects populated catalog UI");
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
  // Confidence is now a secondary signal; coverage leads. The old assertion
  // ("High · 95%") encoded the presentation that made a facility missing a
  // requirement read as broadly fine.
  await expect(page.getByText(/confidence 95%/)).toBeVisible();
  await expect(page.getByText(/2 candidate solutions found/)).toBeVisible();
  await expect(page.getByText(/CNC Machining/)).toBeVisible();
  // Each solution links to its own supply tree.
  await expect(page.getByRole("link", { name: /view supply tree/i }).first()).toBeVisible();
  await page.getByRole("checkbox", { name: /select fablab drome/i }).check();
  await page.getByRole("checkbox", { name: /select community makerspace/i }).check();
  await expect(page.getByText(/2 selected/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /contact selected facilities/i })).toBeEnabled();
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

test("Run Match stays disabled until a facility is selected (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "expects fixture designs");
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

test("near-misses are filtered by a tolerance the design's size bounds (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts mocked results");

  // Four requirements: one facility meets all, one misses a single process.
  const req = (status: string) => ({ status });
  await page.route("**/api/match", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          total_solutions: 2,
          solutions: [
            {
              facility_name: "Complete Works",
              facility_id: "f1",
              confidence: 1,
              rank: 1,
              explanation: {
                requirement_matches: [
                  req("matched"), req("matched"), req("matched"), req("matched"),
                ],
              },
            },
            {
              facility_name: "Nearly There",
              facility_id: "f2",
              confidence: 0.75,
              rank: 2,
              explanation: {
                requirement_matches: [
                  req("matched"), req("matched"), req("matched"), req("unmatched"),
                ],
              },
            },
          ],
        },
      }),
    }),
  );

  await page.goto("/match");
  await page.getByLabel("Search designs").fill("Ventilator");
  await page.getByRole("option", { name: /Open Ventilator/i }).click();
  await page.getByLabel("Laser Fab Lab").check();
  await page.getByRole("button", { name: /run match/i }).click();

  // Default tolerance is one gap, so both appear — and the near-miss says what
  // is missing rather than showing a percentage that reads as "probably fine".
  await expect(page.getByRole("heading", { name: "Complete Works" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nearly There" })).toBeVisible();
  await expect(page.getByText("Missing 1 of 4 requirements")).toBeVisible();
  await expect(page.getByText("Meets every requirement")).toBeVisible();

  // Tightening to zero hides the near-miss.
  const slider = page.getByLabel(/Allow facilities missing up to/);
  await slider.fill("0");
  await expect(page.getByRole("heading", { name: "Nearly There" })).toBeHidden();
  await expect(page.getByRole("heading", { name: "Complete Works" })).toBeVisible();
  await expect(page.getByText(/1 facility is hidden/)).toBeVisible();

  // The ceiling is r-2, so a 4-requirement design can never relax past 2.
  await expect(slider).toHaveAttribute("max", "2");
});

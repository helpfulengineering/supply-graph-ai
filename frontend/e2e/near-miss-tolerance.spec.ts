import { test, expect } from "./mock-api";

/**
 * Characterization baseline for near-miss tolerance (Slice 0 of the frontend
 * revamp integration — see notes/frontend-revamp-integration-plan.md).
 *
 * Regression cover for #355 (cooking) and #356 (manufacturing): the tolerance
 * filter can hide every result, and the slider that reveals them was rendered
 * only inside the already-filtered branch — so once everything was filtered
 * out the user saw a bare "No matches found" with no way back. The fix splits
 * the two empty states: "No matches found" fires only when the API returned
 * nothing; when results exist but are all hidden, the slider renders alongside
 * "No matches within tolerance".
 *
 * This behaviour already has unit cover (MatchView.nearMissTolerance.test.tsx),
 * but those tests mount through MemoryRouter — the exact category the fork's
 * playbook flags as needing a harness rewrite under Next's App Router. These
 * assertions are black-box, so they survive that migration untouched and keep
 * proving the fix while the unit tests are being re-hosted.
 */

/** Requirement matches where `missing` of `total` are unmet, each counted once. */
function requirements(total: number, missing: number) {
  return Array.from({ length: total }, (_, i) => ({
    requirement_value: `requirement-${i}`,
    status: i < total - missing ? "matched" : "unmatched",
  }));
}

/**
 * Five requirements, so the ceiling is 3 (r-2) and the default tolerance is 1.
 * Both facilities miss more than 1, so both start hidden — the state that used
 * to render a dead end.
 */
function hiddenSolutionsResponse(nameA: string, nameB: string) {
  return {
    data: {
      solutions: [
        {
          facility_name: nameA,
          facility_id: "okw-1",
          confidence: 0.6,
          score: 0.6,
          rank: 1,
          explanation_human: "Partial match.",
          explanation: { requirement_matches: requirements(5, 2) },
          tree: { id: "tree-1" },
        },
        {
          facility_name: nameB,
          facility_id: "okw-2",
          confidence: 0.4,
          score: 0.4,
          rank: 2,
          explanation_human: "Partial match.",
          explanation: { requirement_matches: requirements(5, 3) },
          tree: { id: "tree-2" },
        },
      ],
      coverage_gaps: [],
      human_summary: { executive: "2 candidate solutions found." },
      total_solutions: 2,
      solution_id: "sol-1",
    },
  };
}

const emptyResponse = {
  data: {
    solutions: [],
    coverage_gaps: [],
    human_summary: { executive: "No solutions found." },
    total_solutions: 0,
    solution_id: "sol-empty",
  },
};

async function runManufacturingMatch(page: import("@playwright/test").Page) {
  await page.goto("/match");
  await page.getByLabel("Search designs").fill("Ventilator");
  await page.getByRole("option", { name: /Open Ventilator/i }).click();
  await page.getByLabel("Laser Fab Lab").check();
  await page.getByRole("button", { name: /run match/i }).click();
}

async function runCookingMatch(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    localStorage.setItem("ohm-domain", "cooking");
  });
  await page.goto("/match?recipe_id=recipe-1");
  await page.getByRole("checkbox", { name: "Community Kitchen" }).check();
  await page.getByRole("button", { name: "Run Match" }).click();
}

test("manufacturing: results hidden by tolerance keep the slider reachable (#356)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.route("**/v1/api/match", (route) =>
    route.fulfill({ json: hiddenSolutionsResponse("Partial Works", "Barely There") }),
  );

  await runManufacturingMatch(page);

  // The regression: this must NOT be the "API returned nothing" empty state.
  await expect(page.getByText("No matches within tolerance")).toBeVisible();
  await expect(page.getByText("No matches found")).toHaveCount(0);

  // The escape hatch renders even though zero results are showing.
  const slider = page.locator("#near-miss-tolerance");
  await expect(slider).toBeVisible();
  await expect(page.getByText("Allow facilities missing up to 1 requirement")).toBeVisible();
  await expect(page.getByText(/2 facilities are hidden at this setting/)).toBeVisible();
  await expect(page.getByText(/This design has 5 requirements/)).toBeVisible();

  // Raising tolerance to 2 reveals the closer of the two, and only that one.
  await slider.fill("2");
  await expect(page.getByRole("heading", { name: "Partial Works" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Barely There" })).toHaveCount(0);
  await expect(page.getByText(/1 facility is hidden at this setting/)).toBeVisible();

  // At the ceiling both are visible and nothing is hidden.
  await slider.fill("3");
  await expect(page.getByRole("heading", { name: "Partial Works" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Barely There" })).toBeVisible();
  await expect(page.getByText(/hidden at this setting/)).toHaveCount(0);
});

test("manufacturing: an empty API result still reads as no matches found", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.route("**/v1/api/match", (route) => route.fulfill({ json: emptyResponse }));

  await runManufacturingMatch(page);

  // The other side of the split: zero solutions is a genuinely empty result,
  // and the tolerance control has nothing to offer.
  await expect(page.getByText("No matches found")).toBeVisible();
  await expect(page.getByText("No matches within tolerance")).toHaveCount(0);
  await expect(page.locator("#near-miss-tolerance")).toHaveCount(0);
});

test("cooking: results hidden by tolerance keep the slider reachable (#355)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.route("**/v1/api/match", (route) =>
    route.fulfill({ json: hiddenSolutionsResponse("Slow Kitchen", "Sparse Kitchen") }),
  );

  await runCookingMatch(page);

  await expect(page.getByText("No matches within tolerance")).toBeVisible();
  await expect(page.getByText("No matches found")).toHaveCount(0);

  const slider = page.locator("#near-miss-tolerance");
  await expect(slider).toBeVisible();
  await expect(page.getByText("Allow kitchens missing up to 1 requirement")).toBeVisible();
  await expect(page.getByText(/2 kitchens are hidden at this setting/)).toBeVisible();
  await expect(page.getByText(/This recipe has 5 requirements/)).toBeVisible();

  await slider.fill("3");
  await expect(page.getByRole("heading", { name: "Slow Kitchen" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sparse Kitchen" })).toBeVisible();
});

test("cooking: an empty API result still reads as no matches found", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.route("**/v1/api/match", (route) => route.fulfill({ json: emptyResponse }));

  await runCookingMatch(page);

  await expect(page.getByText("No matches found")).toBeVisible();
  await expect(page.getByText("No matches within tolerance")).toHaveCount(0);
  await expect(page.locator("#near-miss-tolerance")).toHaveCount(0);
});

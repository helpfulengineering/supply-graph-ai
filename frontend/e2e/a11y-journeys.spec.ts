import { expect, test } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

// Accessibility coverage across the v1 journeys (mocked lane — several routes
// need fixture ids). Catches contrast/label regressions the per-journey specs
// otherwise miss.
const ROUTES = [
  "/",
  "/okh",
  "/okh/okh-0001",
  "/okh/new",
  "/okh/generate",
  "/facilities",
  "/facilities/okw-1",
  "/match",
  "/packages",
  "/packages/demo/widget/1.0.0",
  "/solutions",
  "/assets",
  "/assets/11111111-1111-4111-8111-111111111111",
  "/assets/11111111-1111-4111-8111-111111111111/triage",
  // With results on the page, not just the unsearched state: the salvage rows
  // and their claim controls only render after a query, and a scan of the
  // empty form would report the surface as clean without seeing it.
  "/assets/salvage?component=Pump",
];

for (const route of ROUTES) {
  test(`no serious a11y violations: ${route}`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "real-api", "uses fixture ids");
    await page.goto(route);
    await expectNoA11yViolations(page);
  });
}

// --- Populated states ------------------------------------------------------
//
// Scanning a route in its INITIAL state misses most of the interesting surface:
// results lists, editors, and anything that renders only after a request. The
// tiered editor shipped 19 serious contrast violations precisely because it
// appears only after a successful generation — no route-level scan ever saw it,
// and adding /okh/generate to the list above would NOT have caught it either,
// since that route renders just a URL box.
//
// These drive each journey to the state a user actually reads, then scan.

const GENERATED_MANIFEST = {
  title: "Open Source Rover",
  version: "1.0.0",
  function: "",
  documentation_language: "en",
  licensor: { name: "JPL" },
  license: { hardware: "Apache-2.0" },
  manufacturing_processes: ["3D Printing", "Laser Cutting"],
  materials: [{ name: "PLA" }],
  stray_field: "kept",
};

test("no serious a11y violations: generate result + tiered editor", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  const jobId = "job-a11y-1";
  await page.route("**/api/okh/generate-from-url/jobs", (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        batch_id: "batch-a11y",
        jobs: [{ job_id: jobId, url: "https://github.com/nasa-jpl/rover" }],
      }),
    });
  });
  await page.route(`**/api/okh/generate-from-url/jobs/${jobId}`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: jobId,
        state: "SUCCESS",
        fraction: 1,
        manifest: GENERATED_MANIFEST,
        // A missing required field renders the "not extracted" markers — the
        // exact elements that carried the contrast failures.
        quality_report: {
          missing_required_fields: ["function"],
          recommendations: ["Add a description"],
        },
      }),
    }),
  );

  await page.goto("/okh/generate");
  await page
    .getByLabel(/Repository URL/i)
    .fill("https://github.com/nasa-jpl/rover");
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByLabel("Title")).toBeVisible();

  await expectNoA11yViolations(page);

  // The long tail is collapsed by default; expand it, or half the editor is
  // never scanned.
  await page.getByText(/Show everything else/).click();
  await expectNoA11yViolations(page);
});

test("no serious a11y violations: guided new-design form", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts client behaviour");
  await page.goto("/okh/new");
  await expect(page.getByLabel("Title")).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("radio", { name: "Paste JSON" }).click();
  await expect(page.getByLabel("JSON")).toBeVisible();
  await expectNoA11yViolations(page);
});

test("no serious a11y violations: match results", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await page.goto("/match");
  await page.getByLabel("Search designs").fill("Ventilator");
  await page.getByRole("option", { name: /Open Ventilator/i }).click();
  await page.getByLabel("Laser Fab Lab").check();
  await page.getByRole("button", { name: /run match/i }).click();
  await expect(
    page.getByRole("heading", { name: "FabLab Drome" }),
  ).toBeVisible();

  await expectNoA11yViolations(page);
});

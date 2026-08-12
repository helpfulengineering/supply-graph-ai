import { test, expect } from "./mock-api";

/**
 * Real-API lane coverage, backed by the deterministic demo world that
 * `scripts/seed_demo_data.py` writes.
 *
 * The rest of the suite runs mocked and skips on `real-api` because it asserts
 * fixture data — which left the live-backend lane checking little more than
 * "the page loaded". These tests are the inverse: they only run against the
 * real API, and they assert the seeded world specifically, so the lane exercises
 * the actual service, storage, and matching engine rather than route handlers.
 *
 * Requires the demo data:  make seed-demo   (idempotent; ids are derived, so
 * reseeding never invalidates a deep link).
 *
 * Assertions key off titles and relationships, never generated ids or counts of
 * things the live backend also sources — the network surface unions local OKW
 * with Maps of Making, so totals there are not ours to predict.
 */

const DEMO_DESIGNS = [
  "Open Ventilator",
  "Face Shield",
  "Solar Food Dryer",
  "Grain Mill",
  "Bias Tape Maker",
  "Wind Turbine Blade Jig",
  "Water Quality Sensor",
  "Microscope Stage",
  "Peristaltic Pump",
  "Soil Test Meter",
];

test("catalog lists every seeded design", async ({ page }) => {
  await page.goto("/okh");
  await expect(
    page.getByRole("heading", { name: /open hardware designs/i }),
  ).toBeVisible();
  for (const title of DEMO_DESIGNS) {
    await expect(
      page.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();
  }
});

test("category facet narrows to the designs that derive it", async ({
  page,
}) => {
  await page.goto("/okh");
  // Medical & PPE is derived from "ventilator" / "shield", so exactly the two
  // medical designs carry it. Derivation lives in features/okh/categories.ts.
  await page.getByRole("checkbox", { name: /Medical & PPE/ }).click();
  await expect(page).toHaveURL(/category=Medical/);
  await expect(
    page.getByRole("heading", { name: "Open Ventilator" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Face Shield" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Grain Mill" })).toBeHidden();
});

test("search narrows the catalog and survives a reload", async ({ page }) => {
  await page.goto("/okh");
  await page.getByPlaceholder(/search designs/i).fill("microscope");
  await expect(page).toHaveURL(/q=microscope/);
  await expect(
    page.getByRole("heading", { name: "Microscope Stage" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Grain Mill" })).toBeHidden();

  // The catalog's whole state lives in the URL; a cold load must restore it.
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Microscope Stage" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Grain Mill" })).toBeHidden();
});

test("a design deep-links to its detail page", async ({ page }) => {
  await page.goto("/okh");
  const link = page.locator('a[href^="/okh/"]').first();
  const href = await link.getAttribute("href");
  expect(href).toBeTruthy();

  // Seeded ids are uuid5-derived, so this URL is stable across reseeds.
  await page.goto(href!);
  await expect(page.getByRole("heading").first()).toBeVisible();
  await expect(page.getByText(/not found/i)).toHaveCount(0);
});

test("matching a single-source design yields exactly one solution", async ({
  page,
}) => {
  // Microscope Stage needs precision_grinding, which only Rotterdam Precision
  // Works has. One design, one buildable facility, one solution — the tightest
  // assertion the seeded world supports.
  await page.goto("/match");
  await page.getByText("Microscope Stage", { exact: true }).first().click();
  await page
    .getByText(/select all visible/i)
    .first()
    .click();

  const run = page.getByRole("button", { name: /run match/i }).first();
  await expect(run).toBeEnabled();
  await run.click();

  await expect(page.locator('a[href*="/visualization/"]')).toHaveCount(1, {
    timeout: 30_000,
  });
});

test("a match carries through to a rendered supply tree", async ({ page }) => {
  await page.goto("/match");
  await page.getByText("Bias Tape Maker", { exact: true }).first().click();
  await page
    .getByText(/select all visible/i)
    .first()
    .click();
  await page
    .getByRole("button", { name: /run match/i })
    .first()
    .click();

  const tree = page.locator('a[href*="/visualization/"]').first();
  await expect(tree).toBeVisible({ timeout: 30_000 });

  // Follow the link rather than re-reading its href and navigating: the match
  // result list re-renders as solutions settle, so a href captured a moment
  // earlier can belong to a detached element by the time it is used.
  await tree.click();
  await page.waitForURL(/\/visualization\//, { timeout: 30_000 });

  await expect(page.getByRole("heading", { name: /supply tree/i })).toBeVisible(
    {
      timeout: 30_000,
    },
  );
  // The graph (cytoscape) and the facility chart (echarts) both draw to canvas;
  // their presence is what proves the client-only boundaries actually mounted.
  await expect(page.locator("canvas").first()).toBeVisible({ timeout: 30_000 });
});

test("seeded facilities appear on the network surface", async ({ page }) => {
  await page.goto("/facilities");
  // This surface unions local OKW with Maps of Making — thousands of spaces on
  // a live instance — so wait for the search control to exist before driving
  // it, and assert our record is present rather than asserting a total.
  const search = page.getByLabel(/search by name/i);
  await expect(search).toBeVisible({ timeout: 30_000 });
  await search.fill("Rotterdam");
  await expect(page.getByText("Rotterdam Precision Works").first()).toBeVisible(
    {
      timeout: 30_000,
    },
  );
});

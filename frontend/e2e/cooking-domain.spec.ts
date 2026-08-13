import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

/**
 * Characterization baseline for the cooking domain (Slice 0 of the frontend
 * revamp integration — see notes/frontend-revamp-integration-plan.md).
 *
 * The contributor's fork branched before the cooking domain landed, and its
 * Next.js `app/` shell contains no recipe or kitchen route. Git will merge
 * `DomainPanel.tsx` and `useDomainPreference.ts` cleanly regardless: the files
 * arrive, the wiring does not. Nothing in the existing suite would notice.
 *
 * These are black-box assertions against user-visible behaviour, so they must
 * survive the Vite -> Next migration byte-for-byte. If a slice needs to edit
 * this file, that is a deliberate behaviour change and belongs in its own PR
 * with a stated reason.
 */

/** The domain is a browser-local preference; seed it before first paint. */
async function useCookingDomain(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    localStorage.setItem("ohm-domain", "cooking");
  });
}

test("cooking domain browses recipes at /okh", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "expects mocked recipe catalog");
  await useCookingDomain(page);
  await page.goto("/okh");

  await expect(page.getByRole("heading", { name: "Recipes", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sourdough Loaf" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Miso Soup" })).toBeVisible();

  // Counts are the card's only summary line — a silent shape change in the
  // Recipe type would surface here rather than as an empty card.
  await expect(page.getByText("4 ingredients · 4 steps")).toBeVisible();
  await expect(page.getByText("3 ingredients · 2 steps")).toBeVisible();

  await expectNoA11yViolations(page);
});

test("cooking domain browses kitchens at /facilities", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "expects mocked kitchen catalog");
  await useCookingDomain(page);
  await page.goto("/facilities");

  await expect(page.getByRole("heading", { name: "Kitchens", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Community Kitchen" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Pop-Up Canteen" })).toBeVisible();

  await expectNoA11yViolations(page);
});

test("a recipe card opens its detail page", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "expects mocked recipe catalog");
  await useCookingDomain(page);
  await page.goto("/okh");

  await page.getByRole("link", { name: "Sourdough Loaf" }).click();

  await expect(page).toHaveURL(/\/okh\/recipe-1$/);
  await expect(page.getByRole("heading", { name: "Sourdough Loaf", level: 1 })).toBeVisible();

  // The three panels are the whole point of the detail page.
  await expect(page.getByRole("heading", { name: "Ingredients" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Instructions" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Equipment" })).toBeVisible();
  await expect(page.getByText("starter")).toBeVisible();
  await expect(page.getByText("Bulk ferment")).toBeVisible();
  await expect(page.getByText("dutch oven")).toBeVisible();

  // Breadcrumb back to the list.
  await expect(page.getByRole("link", { name: "Recipes" }).first()).toBeVisible();

  await expectNoA11yViolations(page);
});

test("Run Match on a recipe card preselects that recipe", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "expects mocked recipe catalog");
  await useCookingDomain(page);
  await page.goto("/okh");

  await page.getByRole("button", { name: "Run Match ⚡" }).first().click();

  await expect(page).toHaveURL(/\/match\?recipe_id=recipe-1$/);
  await expect(page.getByRole("heading", { name: "Match a Recipe", level: 1 })).toBeVisible();
});

test("Run Match on a recipe detail page preselects that recipe", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "expects mocked recipe catalog");
  await useCookingDomain(page);
  await page.goto("/okh/recipe-2");

  await page.getByRole("button", { name: "⚡ Run Match" }).click();

  await expect(page).toHaveURL(/\/match\?recipe_id=recipe-2$/);
  await expect(page.getByRole("heading", { name: "Match a Recipe", level: 1 })).toBeVisible();
});

test("cooking match guards on recipe and kitchen selection", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "expects mocked catalogs");
  await useCookingDomain(page);

  // No recipe in the URL: the view asks for one before it will run.
  await page.goto("/match");
  await expect(page.getByRole("heading", { name: "Match a Recipe", level: 1 })).toBeVisible();
  await expect(
    page.getByText("Search and select a recipe above before running a match."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "⚡ Run Match" })).toBeDisabled();

  // Recipe preselected but no kitchens chosen: still guarded, different reason.
  await page.goto("/match?recipe_id=recipe-1");
  await expect(
    page.getByText("Select at least one kitchen below before running a match."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "⚡ Run Match" })).toBeDisabled();

  await expectNoA11yViolations(page);
});

test("the domain toggle reshapes primary nav and persists across reloads", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "browser-local preference");
  const nav = page.getByRole("navigation", { name: "Primary navigation" });

  // A fresh browser is manufacturing, and the server default agrees.
  await page.goto("/settings/domain");
  await expect(nav.getByRole("link", { name: "Designs" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Facilities" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Packages" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Match" })).toBeVisible();

  await page.getByRole("radio", { name: /Cooking/ }).check();

  // Cooking renames two entries and drops the other two entirely.
  await expect(nav.getByRole("link", { name: "Recipes" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Kitchens" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Packages" })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "Match" })).toHaveCount(0);

  // localStorage owns the choice once it exists, so a reload keeps it.
  await page.reload();
  await expect(nav.getByRole("link", { name: "Recipes" })).toBeVisible();
  await expect(page.getByRole("radio", { name: /Cooking/ })).toBeChecked();

  await expectNoA11yViolations(page);
});

test("a stored preference outranks the server default", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "browser-local preference");
  // The mocked /utility/domains reports default_domain "manufacturing"; a
  // browser that already chose cooking must not be reset by it.
  await useCookingDomain(page);
  await page.goto("/okh");

  await expect(page.getByRole("heading", { name: "Recipes", level: 1 })).toBeVisible();
});

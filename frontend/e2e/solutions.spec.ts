import { test, expect } from "./mock-api";

/**
 * The saved-solutions browse (slice #195), rebuilt.
 *
 * It was removed once for listing every visitor's searches out of unscoped
 * shared storage, and it is back because the listing is now scoped server-side
 * to the account behind the API key. The first test below is the one that
 * matters: without a key this page must offer nothing to look at. It is the UI
 * half of tests/api/test_solution_scoping.py, which asserts the same property
 * where it is actually enforced.
 */

/** The session key shape the app reads, matching settings.spec.ts. */
async function withKey(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });
}

test("without a key the empty list is explained rather than reported as loss", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an empty response");
  // The server answers an anonymous caller with nothing; this is that response.
  await page.route("**/v1/api/supply-tree/solutions**", (route) =>
    route.fulfill({ json: { data: { result: [] } } }),
  );
  await page.goto("/solutions");
  await expect(
    page.getByRole("heading", { name: /saved solutions/i, level: 1 }),
  ).toBeVisible();
  await expect(page.getByText(/connect an api key/i)).toBeVisible();
  // Not "No saved solutions" — that would tell someone whose matches are all
  // still there that they are gone.
  await expect(page.getByText(/^no saved solutions$/i)).toBeHidden();
});

test("lists the caller's solutions and opens one in the explorer", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await withKey(page);
  await page.goto("/solutions");

  await expect(
    page.getByRole("heading", { name: "Foldable Solar Dryer" }),
  ).toBeVisible();
  // The primary facility rides alongside the title so a row is identifiable
  // without opening it.
  await expect(page.getByText("FabLab Drome")).toBeVisible();
  await expect(page.getByText("95%")).toBeVisible();

  await page.getByRole("link", { name: /foldable solar dryer/i }).click();
  await expect(page).toHaveURL(/\/visualization\/sol-1/);
  await expect(
    page.getByRole("heading", { name: "Supply Tree", level: 1 }),
  ).toBeVisible();
});

test("shows the empty state when the account has no solutions", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "forces an empty response");
  await withKey(page);
  await page.route("**/v1/api/supply-tree/solutions**", (route) =>
    route.fulfill({ json: { data: { result: [] } } }),
  );
  await page.goto("/solutions");
  await expect(page.getByText(/no saved solutions/i)).toBeVisible();
});

test("bare /visualization lands on the browse rather than home", async ({
  page,
}) => {
  await page.goto("/visualization");
  await expect(page).toHaveURL(/\/solutions/);
});

import { expect, test } from "./mock-api";

/**
 * The asset journey: fleet → unit → triage → report → sourcing → salvage.
 *
 * Fixture ids are UUIDs because the API declares them as such. A readable
 * placeholder makes the real backend answer 422, and this lane would then be
 * asserting against an error panel — the failure mode mock-api.ts records in
 * its own docstring.
 */
const ASSET = "11111111-1111-4111-8111-111111111111";

// eslint-disable-next-line no-empty-pattern -- Playwright requires the destructuring form here, and this hook needs no fixture.
test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "uses fixture ids");
});

test("the fleet lists units grouped by lifecycle status", async ({ page }) => {
  await page.goto("/assets");

  await expect(
    page.getByRole("heading", { name: "Assets in the field" }),
  ).toBeVisible();

  // Lifecycle order, not alphabetical: "Active" precedes "Under triage", and
  // "Condemned" would otherwise open the queue.
  const groups = page.locator("#main section h2");
  await expect(groups.first()).toHaveText(/Active/);

  await expect(page.getByRole("link", { name: /OHM-0042/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /OHM-0043/ })).toBeVisible();

  // The unit nobody has looked at says so, rather than reading "0 of 0".
  await expect(
    page.getByRole("link", { name: /OHM-0043/ }).getByText("never triaged"),
  ).toBeVisible();
});

test("filtering to nothing is a different empty state from an empty fleet", async ({
  page,
}) => {
  await page.goto("/assets");
  await page
    .getByPlaceholder("Tag, location, or design")
    .fill("nothing matches this");

  await expect(
    page.getByText("No assets match the current filters"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Clear filters" }),
  ).toBeVisible();
  // The "no assets registered" copy would tell someone with a filter on that
  // their fleet is empty.
  await expect(page.getByText("No assets registered")).toHaveCount(0);
});

test("a unit shows its components, report, and anchored crumb", async ({
  page,
}) => {
  await page.goto(`/assets/${ASSET}`);

  await expect(
    page.getByRole("heading", { name: "OHM-0042", level: 1 }),
  ).toBeVisible();

  // All three crumb terms link, because the page has no tab strip and these
  // anchors are the only navigation to those sections.
  const crumb = page.locator("#main [data-crumb] a");
  await expect(crumb).toHaveCount(3);
  await expect(crumb.nth(0)).toHaveAttribute("href", "#components");

  await expect(
    page.getByRole("heading", { name: /^Components/ }),
  ).toBeVisible();
  await expect(page.getByText("Impeller cracked").first()).toBeVisible();

  // The report teaches its own vocabulary where it uses it.
  await expect(
    page.getByText(
      "The design marks it salvageable — take one from another unit.",
    ),
  ).toBeVisible();
});

test("sourcing stays behind a button and says why when it cannot run", async ({
  page,
}) => {
  await page.goto(`/assets/${ASSET}`);

  // The fixture's triage found nothing needing a part, so the control explains
  // itself rather than running a fleet-wide scan that would return nothing.
  const button = page.getByRole("button", { name: "Resolve sourcing" });
  await expect(button).toBeDisabled();
  await expect(
    page.getByText("Triage found no components needing a part.").first(),
  ).toBeVisible();
});

test("triage shows follow-up flags only where the condition implies work", async ({
  page,
}) => {
  await page.goto(`/assets/${ASSET}/triage`);

  await expect(
    page.getByRole("heading", { name: "Triage", level: 1 }),
  ).toBeVisible();
  await expect(page.getByText("1 of 2 assessed")).toBeVisible();

  // Pump assembly arrived damaged, so its three tri-state groups are shown and
  // the recorded `repair_feasible: false` is the selected segment — null and
  // false being different answers is the reason these are not checkboxes.
  const repair = page.getByRole("radiogroup", {
    name: "Repair feasible for Pump assembly",
  });
  await expect(repair).toBeVisible();
  // exact, or "No" also matches "Not stated".
  await expect(
    repair.getByRole("radio", { name: "No", exact: true }),
  ).toHaveAttribute("aria-checked", "true");

  // Control board has no recorded condition, so asking about repair would be
  // three controls for a question nobody has reached yet.
  await expect(
    page.getByRole("radiogroup", { name: "Repair feasible for Control board" }),
  ).toHaveCount(0);

  // Nothing changed yet, so there is nothing to record.
  await expect(
    page.getByRole("button", { name: "Record triage" }),
  ).toBeDisabled();
});

test("choosing a condition enables recording", async ({ page }) => {
  await page.goto(`/assets/${ASSET}/triage`);

  await page
    .getByRole("radiogroup", { name: "Condition of Control board" })
    .getByRole("radio", { name: "Intact" })
    .click();

  await expect(
    page.getByRole("button", { name: "Record triage" }),
  ).toBeEnabled();
});

test("salvage distinguishes an unsearched page from an empty result", async ({
  page,
}) => {
  await page.goto("/assets/salvage");

  // Unsearched: says what the page is for, and refuses to search without the
  // one field the API requires.
  await expect(page.getByText("Search the fleet for a part")).toBeVisible();
  await expect(page.getByRole("button", { name: "Search" })).toBeDisabled();
  await expect(
    page.getByText("Enter a component name or a part number to search."),
  ).toBeVisible();

  await page.goto("/assets/salvage?component=Pump");
  await expect(page.getByText("1 part found")).toBeVisible();
  // The result names the unit the part is currently in, and links to it.
  await expect(page.getByRole("link", { name: "OHM-0043" })).toBeVisible();
});

test("the sitemap and keyboard both reach the fleet", async ({ page }) => {
  await page.goto("/");
  await page.waitForSelector("html[data-keys-ready]");

  await page.keyboard.press("g");
  await page.keyboard.press("a");

  // The chrome carries theme and mode in the query string, so the chord
  // lands on /assets with them attached.
  await expect(page).toHaveURL(/\/assets(\?|$)/);
});

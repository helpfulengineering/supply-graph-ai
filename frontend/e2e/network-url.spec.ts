import { expect } from "@playwright/test";
import { test } from "./mock-api";

/**
 * The network surface follows its own address.
 *
 * Its filters, view, page, and name query are seeded from the query string and
 * then owned locally. That was correct while the view was the only thing
 * writing to them, and stopped being correct once the hero crumb linked to
 * `?source=...`: a same-route link replaces the query string without
 * remounting, so a seed-once initialiser never saw it. The link moved the
 * address, drew its underline and focus ring, and changed nothing on the page.
 *
 * Back has always had the same defect and no test — the address returned to the
 * previous filter while the list stayed where it was.
 */

test("the crumb's source terms filter the network", async ({ page }) => {
  await page.goto("/facilities");
  await page.locator("#main").waitFor({ state: "visible" });

  const source = page.getByLabel("Source");
  await expect(source).toHaveValue("");

  await page.getByRole("link", { name: "local", exact: true }).click();
  await expect.poll(() => page.url()).toContain("source=local");
  // The assertion the href alone did not satisfy.
  await expect(source).toHaveValue("local");

  await page.getByRole("link", { name: "federated", exact: true }).click();
  await expect.poll(() => page.url()).toContain("source=mom");
  await expect(source).toHaveValue("mom");
});

test("Back steps between the crumb's sources", async ({ page }) => {
  await page.goto("/facilities");
  await page.locator("#main").waitFor({ state: "visible" });
  const source = page.getByLabel("Source");

  await page.getByRole("link", { name: "local", exact: true }).click();
  await expect(source).toHaveValue("local");
  await page.getByRole("link", { name: "federated", exact: true }).click();
  await expect(source).toHaveValue("mom");

  // Back through the crumb, not through the filter panel. `syncUrl` uses
  // replace on purpose — narrowing a filter is a refinement, not a step to go
  // back from — so only the crumb's links leave history entries, and this is
  // the behaviour the adopt-the-address effect has to get right.
  await page.goBack();
  await expect(source).toHaveValue("local");
});

test("a filter set in the address survives into the match flow", async ({
  page,
}) => {
  // The seeded path, which worked before and has to keep working: arriving
  // from elsewhere mounts the view fresh.
  await page.goto("/facilities?source=mom");
  await page.locator("#main").waitFor({ state: "visible" });
  await expect(page.getByLabel("Source")).toHaveValue("mom");
});

test("typing in the search box is not clobbered by the address", async ({
  page,
}) => {
  // The first version of the adopt-the-address effect took the name query from
  // the URL too. `syncUrl` uses router.replace, which lands asynchronously, so
  // typing "ab" could be overtaken by the navigation carrying "a" and the box
  // would jump backwards. Nothing outside this component writes `q` on this
  // route, so the effect leaves it alone — and this is the reason.
  await page.goto("/facilities");
  await page.locator("#main").waitFor({ state: "visible" });

  const search = page.getByLabel("Search by name");
  await search.pressSequentially("Laser", { delay: 30 });

  await expect(search).toHaveValue("Laser");
  await expect.poll(() => page.url()).toContain("q=Laser");
});

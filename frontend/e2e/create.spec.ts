import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

test("create design page renders", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked lane");
  await page.goto("/okh/new");
  await expect(page.getByRole("heading", { name: "New design" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create" })).toBeVisible();
  await expectNoA11yViolations(page);
});

test("create facility page renders", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked lane");
  await page.goto("/facilities/new");
  await expect(
    page.getByRole("heading", { name: "New facility" }),
  ).toBeVisible();
  await expect(page.getByLabel("Name *")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create facility" }),
  ).toBeVisible();
  await expect(page.getByLabel("3D Printing")).toBeVisible();
  await expectNoA11yViolations(page);
});

test("new design offers a guided form, not just raw JSON (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts client behaviour");

  await page.goto("/okh/new");

  // Guided is the default: requiring hand-authored OKH JSON is the barrier OHM
  // exists to remove.
  await expect(page.getByRole("radio", { name: "Guided" })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  await expect(page.getByLabel("Title")).toBeVisible();
  await expect(page.getByLabel("Licensor name")).toBeVisible();

  // Saving is gated until the required fields are filled.
  await expect(
    page.getByRole("button", { name: /Create design/ }),
  ).toBeDisabled();

  // The JSON route is still reachable for people who already have a manifest.
  await page.getByRole("radio", { name: "Paste JSON" }).click();
  await expect(page.getByLabel("JSON")).toBeVisible();
});

import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

test("an admin lists invites and can mint one", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked identity APIs only");
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });

  await page.goto("/settings/invites");
  await expect(page.getByRole("heading", { name: "Invites" })).toBeVisible();
  await expect(
    page.getByText("11111111-1111-4111-8111-111111111111"),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Mint invite" })).toBeVisible();
  await expectNoA11yViolations(page);
});

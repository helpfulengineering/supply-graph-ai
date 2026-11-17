import { test, expect } from "@playwright/test";
import { api } from "./api";
import { field, ohm } from "./ohm";
import { newVisitor, pasteToken } from "./people";
import { shot } from "./shot";
import {
  loadWorld,
  requireOperator,
  requirePerson,
} from "./world";

/**
 * Part 5 of the membership runbook: attribute a design she already has (#589).
 */
test.describe("@membership part 5: attribute a design later", () => {
  test.describe.configure({ mode: "serial" });

  test("Ada attributes the unaffiliated design, then clears it", async ({
    browser,
  }, testInfo) => {
    const ada = await requirePerson("ada");
    const spaceDid = loadWorld().spaceDid;
    const designId = loadWorld().designs?.unaffiliated;
    expect(spaceDid).toBeTruthy();
    expect(designId).toBeTruthy();

    const { context, page } = await newVisitor(browser);
    try {
      await pasteToken(page, ada.token, ada.name);
      await page.goto("/account");
      await page
        .getByRole("checkbox", { name: /Field pump, unaffiliated/i })
        .check();
      if (!spaceDid || !designId) {
        throw new Error("spaceDid or designId missing");
      }
      await page
        .getByLabel(/Organisation for selected designs/i)
        .selectOption(spaceDid);
      await page
        .getByRole("button", { name: /Attribute 1 design to Field org/i })
        .click();
      await page.goto(`/okh/${designId}`);
      await expect(page.getByText(spaceDid, { exact: false })).toBeVisible();
      await shot(page, testInfo, "part5-01-attributed");

      await page.goto("/account");
      await page
        .getByRole("checkbox", { name: /Field pump, unaffiliated/i })
        .check();
      await page
        .getByLabel(/Organisation for selected designs/i)
        .selectOption("none");
      await page
        .getByRole("button", {
          name: /Remove the organisation from 1 design/i,
        })
        .click();
      await page.goto(`/okh/${designId}`);
      await expect(page.getByText(/^On behalf of$/)).toHaveCount(0);
      await shot(page, testInfo, "part5-02-cleared");
    } finally {
      await context.close();
    }
  });

  test("clear succeeds after unaffiliate; re-add is refused until re-affiliated", async ({
    browser,
  }, testInfo) => {
    const operator = await requireOperator();
    const ada = await requirePerson("ada");
    const spaceDid = loadWorld().spaceDid;
    const designId = loadWorld().designs?.unaffiliated;
    expect(spaceDid).toBeTruthy();
    expect(designId).toBeTruthy();
    if (!spaceDid || !designId) {
      return;
    }

    // Put the organisation back, then unaffiliate Ada.
    await api(ada.token, "PUT", `/api/okh/${designId}/attribution`, {
      on_behalf_of: spaceDid,
    });
    const administered = await ohm(operator.token, [
      "identity",
      // There is no dedicated CLI for listing administered orgs; use the API.
      "whoami",
    ]);
    expect(administered).toBeTruthy();

    // Unaffiliate via the operator's Organisations UI so the grant_id is found.
    const { context: opCtx, page: opPage } = await newVisitor(browser);
    try {
      await pasteToken(opPage, operator.token, operator.name);
      await opPage.goto("/people/organisations");
      await opPage.getByRole("button", { name: "Unaffiliate" }).click();
      await expect(opPage.getByRole("button", { name: "Unaffiliate" })).toHaveCount(
        0,
      );
      await shot(opPage, testInfo, "part5-03-unaffiliated-ada");
    } finally {
      await opCtx.close();
    }

    // Clear still works after unaffiliate.
    const cleared = await api(
      ada.token,
      "PUT",
      `/api/okh/${designId}/attribution`,
      { on_behalf_of: null },
    );
    expect(cleared.status).toBeGreaterThanOrEqual(200);
    expect(cleared.status).toBeLessThan(300);

    // Re-add is refused until she is affiliated again.
    const refused = await api(
      ada.token,
      "PUT",
      `/api/okh/${designId}/attribution`,
      { on_behalf_of: spaceDid },
    );
    expect(refused.status).toBeGreaterThanOrEqual(400);

    // Re-affiliate Ada and put the organisation back on Field pump for later.
    await ohm(operator.token, [
      "identity",
      "affiliate",
      "add",
      ada.did,
      "--space",
      spaceDid,
    ]);
    const fieldPump = loadWorld().designs?.fieldPump;
    if (fieldPump) {
      const put = await api(
        ada.token,
        "PUT",
        `/api/okh/${fieldPump}/attribution`,
        { on_behalf_of: spaceDid },
      );
      expect(put.status).toBeGreaterThanOrEqual(200);
      expect(put.status).toBeLessThan(300);
    }
  });

  test("Bo is refused when attributing Ada's design", async () => {
    const bo = await requirePerson("bo");
    const spaceDid = loadWorld().spaceDid;
    const designId = loadWorld().designs?.unaffiliated;
    expect(spaceDid).toBeTruthy();
    expect(designId).toBeTruthy();
    if (!spaceDid || !designId) {
      return;
    }
    const result = await api(
      bo.token,
      "PUT",
      `/api/okh/${designId}/attribution`,
      { on_behalf_of: spaceDid },
    );
    expect(result.status).toBeGreaterThanOrEqual(400);
  });

  test("pasting Bo's token over Chi's password session makes whoami Bo", async ({
    browser,
  }, testInfo) => {
    // Assertion 5. Chi has a cookie session; Ada was minted without a password.
    const bo = await requirePerson("bo");
    const { context, page } = await newVisitor(browser);
    try {
      await page.goto("/login");
      await page.getByLabel("Username").fill("chi");
      await page.getByLabel("Password").fill("chi-passphrase-for-uat");
      await page.getByRole("button", { name: "Sign in" }).click();
      await page.goto("/account");
      await expect(page.getByText("Chi", { exact: false })).toBeVisible();

      await pasteToken(page, bo.token, bo.name);
      await page.goto("/settings/session");
      const identity = page.getByRole("region", { name: "Current identity" });
      await expect(identity.getByText(bo.name, { exact: true })).toBeVisible();
      await expect(identity.getByText("Chi", { exact: true })).toHaveCount(0);
      await shot(page, testInfo, "part5-04-paste-over-session");
    } finally {
      await context.close();
    }
  });

  test("deleting an account removes the row and shows a toast", async ({
    browser,
  }, testInfo) => {
    // Assertion 6. Create a throwaway account, then delete it from Keys.
    const operator = await requireOperator();
    const account = await ohm(operator.token, [
      "identity",
      "accounts",
      "create",
      "--name",
      "Doomed",
    ]);
    const doomedId = field(account, "id");

    const { context, page } = await newVisitor(browser);
    try {
      await pasteToken(page, operator.token, operator.name);
      await page.goto("/settings/keys");
      await expect(page.getByText("Doomed")).toBeVisible();
      page.once("dialog", (dialog) => dialog.accept());
      // The Delete button next to the Doomed account row.
      const row = page.locator("li").filter({ hasText: "Doomed" });
      await row.getByRole("button", { name: "Delete" }).click();
      await expect(page.getByText("Account deleted")).toBeVisible();
      await expect(
        page.getByRole("region", { name: "Accounts" }).getByText("Doomed"),
      ).toHaveCount(0);
      await shot(page, testInfo, "part5-05-account-deleted");
      // A reload agrees.
      await page.reload();
      await expect(
        page.getByRole("region", { name: "Accounts" }).getByText("Doomed"),
      ).toHaveCount(0);
      void doomedId;
    } finally {
      await context.close();
    }
  });
});

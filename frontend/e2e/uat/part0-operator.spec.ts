import { test, expect } from "@playwright/test";
import { field, ohm, ohmAsBootstrap } from "./ohm";
import { newVisitor } from "./people";
import { shot } from "./shot";
import { resetWorld, saveWorld, type Person } from "./world";

/**
 * Part 0 of the membership runbook: an operator who is a person.
 *
 * The bootstrap key (`API_KEYS`) is a machine credential with no person behind
 * it. This part uses it once, to make an account, a person DID and an admin key
 * for the operator, and from then on the operator is who acts.
 */
test.describe("@membership part 0: an operator who is a person", () => {
  test.describe.configure({ mode: "serial" });

  let operator: Person;

  test("mint the operator", async () => {
    // A new pass starts from an empty world.
    resetWorld();

    const account = await ohmAsBootstrap([
      "identity",
      "accounts",
      "create",
      "--name",
      "Node operator",
    ]);
    const accountId = field(account, "id");
    const identity = await ohmAsBootstrap([
      "identity",
      "identities",
      "create",
      "--account-id",
      accountId,
      "--kind",
      "person",
      "--name",
      "Node operator",
    ]);
    const key = await ohmAsBootstrap([
      "identity",
      "keys",
      "create",
      "--name",
      "operator",
      "--permission",
      "admin",
      "--account-id",
      accountId,
    ]);
    const token = field(key, "token");

    const who = await ohm(token, ["identity", "whoami"]);
    expect(who.permissions, "the operator key is an admin key").toContain(
      "admin",
    );
    expect(
      String(who.subject_did),
      "subject_did is a did:key, so the operator is a person",
    ).toMatch(/^did:key:/);

    operator = {
      name: field(who, "name"),
      accountId,
      did: field(identity, "did"),
      token,
    };
    expect(who.subject_did).toBe(operator.did);
    saveWorld({ operator });
  });

  test("the operator signs in from a signed-out browser", async ({
    browser,
  }, testInfo) => {
    const { context, page } = await newVisitor(browser);
    try {
      await test.step("the menu lists API key before anyone is signed in", async () => {
        await page.goto("/");
        await page.getByRole("button", { name: "Site menu" }).click();
        await page
          .getByRole("dialog", { name: "Site menu" })
          .getByRole("link", { name: "API key" })
          .click();
        await expect(page).toHaveURL(/\/settings\/session$/);
      });

      await test.step("pasting OPERATOR_TOKEN and saving signs the operator in", async () => {
        await page.getByLabel("Token").fill(operator.token);
        await page.getByRole("button", { name: "Save" }).click();
      });

      await test.step("Current identity shows the operator name, the account, and the person DID", async () => {
        const identity = page.getByRole("region", { name: "Current identity" });
        await expect(
          identity.getByText(operator.name, { exact: true }),
        ).toBeVisible();
        await expect(identity.getByText(operator.accountId)).toBeVisible();
        await expect(identity.getByText(operator.did)).toBeVisible();
        await expect(identity.getByRole("alert")).toHaveCount(0);
        await shot(page, testInfo, "part0-01-current-identity");
      });
    } finally {
      await context.close();
    }
  });
});

import { test, expect, type Page, type TestInfo } from "@playwright/test";
import { NODE_NAME, OPERATOR_NAME } from "./env";
import { field, ohm } from "./ohm";
import { newVisitor } from "./people";
import { shot } from "./shot";
import { requireOperator, saveWorld, loadWorld, type Person } from "./world";

/**
 * Part 2 of the membership runbook: invite links (#569).
 *
 * Ada and Bo are minted by part 3. This part proves the registration UI with a
 * throwaway, Chi, who registers through an invite with a real password.
 */
test.describe("@membership part 2: invite links", () => {
  test.describe.configure({ mode: "serial" });

  const FORM = "Create an identity on this node";
  const INVITE_REQUIRED = "An invite is required";
  const CLOSED = "This node does not accept registrations";

  async function setRegistration(
    token: string,
    mode: "open" | "invite" | "closed",
  ) {
    const result = await ohm(token, [
      "identity",
      "registration",
      "--set",
      mode,
    ]);
    expect(field(result, "registration")).toBe(mode);
  }

  async function mintInvite(
    token: string,
    useLimit?: number,
  ): Promise<{ inviteId: string; path: string }> {
    const args = ["identity", "invite", "mint", "--ttl-days", "7"];
    if (useLimit !== undefined) {
      args.push("--use-limit", String(useLimit));
    }
    const minted = await ohm(token, args);
    return {
      inviteId: field(minted, "invite_id"),
      path: `/register?invite=${field(minted, "token")}`,
    };
  }

  async function registerChi(
    page: Page,
    invitePath: string,
    testInfo: TestInfo,
  ): Promise<Person> {
    await page.goto(invitePath);
    await expect(page.getByRole("heading", { name: FORM })).toBeVisible();
    await expect(page.getByText(NODE_NAME, { exact: true })).toBeVisible();
    await expect(page.getByText(OPERATOR_NAME, { exact: true })).toBeVisible();
    await page.getByLabel("Username").fill("chi");
    await page.getByLabel("Password").fill("chi-passphrase-for-uat");
    await page.getByLabel("Display name").fill("Chi");
    await page.getByRole("button", { name: "Register" }).click();
    await expect(page.getByText("Save your recovery code")).toBeVisible();
    await shot(page, testInfo, "part2-01-chi-registered");
    // whoami through the browser session: the cookie is set. For the world we
    // only need Chi's DID, which the account page shows.
    await page.goto("/account");
    const did = await page
      .getByText(/^did:key:/)
      .first()
      .innerText();
    const person: Person = {
      name: "Chi",
      accountId: "",
      did: did.trim(),
      // Chi has a password session, not an API token. Downstream parts that
      // need a cookie session for Chi re-login; the DID is what the invite
      // flow produces.
      token: "",
    };
    const people = { ...(loadWorld().people ?? {}), chi: person };
    saveWorld({ people });
    return person;
  }

  test("a one-use invite registers Chi, then refuses everyone else", async ({
    browser,
  }, testInfo) => {
    const operator = await requireOperator();
    await setRegistration(operator.token, "invite");
    const first = await mintInvite(operator.token, 1);

    const { context: chiContext, page: chiPage } = await newVisitor(browser);
    try {
      await test.step("the form is back, and it still names Field node and Ada's workshop. Register Chi", async () => {
        await registerChi(chiPage, first.path, testInfo);
      });
    } finally {
      await chiContext.close();
    }

    const { context, page } = await newVisitor(browser);
    try {
      await test.step("without an invite, the page says an invite is required", async () => {
        await page.goto("/register");
        await expect(
          page.getByText(INVITE_REQUIRED, { exact: true }),
        ).toBeVisible();
        await expect(page.getByRole("heading", { name: FORM })).toHaveCount(0);
        await shot(page, testInfo, "part2-02-invite-required");
      });

      await test.step("the same one-use link has no uses left", async () => {
        await page.goto(first.path);
        // The node refuses a spent invite. The copy can say "invite" or
        // "required"; what matters is that there is no registration form.
        await expect(page.getByRole("heading", { name: FORM })).toHaveCount(0);
        await expect(page.getByLabel("Username")).toHaveCount(0);
        await shot(page, testInfo, "part2-03-invite-spent");
      });
    } finally {
      await context.close();
    }

    const second = await mintInvite(operator.token);
    const listed = await ohm(operator.token, ["identity", "invite", "list"]);
    expect(Array.isArray(listed)).toBe(true);
    await ohm(operator.token, [
      "identity",
      "invite",
      "revoke",
      second.inviteId,
    ]);

    const { context: revokedCtx, page: revokedPage } =
      await newVisitor(browser);
    try {
      await test.step("a revoked link refuses registration", async () => {
        await revokedPage.goto(second.path);
        await expect(
          revokedPage.getByRole("heading", { name: FORM }),
        ).toHaveCount(0);
        await shot(revokedPage, testInfo, "part2-04-invite-revoked");
      });
    } finally {
      await revokedCtx.close();
    }

    await setRegistration(operator.token, "closed");
    const third = await mintInvite(operator.token, 1);
    const { context: closedCtx, page: closedPage } = await newVisitor(browser);
    try {
      await test.step("closed wins. The link does not register anyone", async () => {
        await closedPage.goto(third.path);
        await expect(
          closedPage.getByText(CLOSED, { exact: true }),
        ).toBeVisible();
        await expect(
          closedPage.getByRole("heading", { name: FORM }),
        ).toHaveCount(0);
        await shot(closedPage, testInfo, "part2-05-closed-beats-invite");
      });
    } finally {
      await closedCtx.close();
    }

    // Leave registration on invite for the rest of the run.
    await setRegistration(operator.token, "invite");
  });
});

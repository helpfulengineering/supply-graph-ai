import { test, expect } from "@playwright/test";
import { field, ohm, OhmError } from "./ohm";
import { newVisitor, pasteToken } from "./people";
import { shot } from "./shot";
import {
  mintPerson,
  requireOperator,
  requirePerson,
  saveWorld,
  loadWorld,
} from "./world";

/**
 * Part 3 of the membership runbook: a coordinator (#573).
 *
 * Mint Ada and Bo (script-first), grant Bo coordinate, then prove Bo's reach
 * and Ada's privacy through the browser.
 */
test.describe("@membership part 3: a coordinator", () => {
  test.describe.configure({ mode: "serial" });

  test("mint Ada and Bo, grant Bo coordinate", async () => {
    const operator = await requireOperator();
    const ada = await mintPerson(operator, "ada", "Ada");
    const bo = await mintPerson(operator, "bo", "Bo");
    const grant = await ohm(operator.token, [
      "identity",
      "coordinate",
      bo.did,
    ]);
    const expires = field(grant, "expires_at");
    const days =
      (Date.parse(expires) - Date.now()) / (1000 * 60 * 60 * 24);
    expect(days, "coordinate lasts about 180 days").toBeGreaterThan(170);
    expect(days).toBeLessThan(190);
    // Keep the DIDs the later parts read.
    expect(ada.did).toMatch(/^did:key:/);
    expect(bo.did).toMatch(/^did:key:/);
  });

  test("Bo's Settings shows Invites and Members, not Storage or Keys", async ({
    browser,
  }, testInfo) => {
    const bo = await requirePerson("bo");
    const { context, page } = await newVisitor(browser);
    try {
      await pasteToken(page, bo.token, bo.name);
      await page.goto("/settings/session");
      const nav = page.getByRole("navigation", { name: "Settings" });
      await expect(nav.getByRole("link", { name: "Invites" })).toBeVisible();
      await expect(nav.getByRole("link", { name: "Members" })).toBeVisible();
      await expect(
        nav.getByRole("link", { name: "Storage" }),
      ).toHaveCount(0);
      await expect(
        nav.getByRole("link", { name: "LLM providers" }),
      ).toHaveCount(0);
      await expect(
        nav.getByRole("link", { name: "Keys & accounts" }),
      ).toHaveCount(0);
      await shot(page, testInfo, "part3-01-bo-settings");
    } finally {
      await context.close();
    }
  });

  test("Ada's facility is on Bo's Members row without the street", async ({
    browser,
  }, testInfo) => {
    const ada = await requirePerson("ada");
    const bo = await requirePerson("bo");
    const street = "12 Hidden Lane";

    const { context: adaCtx, page: adaPage } = await newVisitor(browser);
    try {
      await pasteToken(adaPage, ada.token, ada.name);
      await adaPage.goto("/facilities/new");
      await adaPage.getByLabel(/^Name/).fill("Ada's workshop floor");
      await adaPage.getByLabel(/^City/).fill("Portland");
      await adaPage.getByLabel(/^Country/).fill("US");
      await adaPage.getByLabel("Street (optional)").fill(street);
      // Pick the first process the taxonomy offers.
      const process = adaPage.getByLabel(/3D Printing/i);
      if (await process.count()) {
        await process.check();
      } else {
        // Taxonomy labels vary; fall back to the first checkbox in Processes.
        await adaPage
          .getByRole("heading", { name: "Processes" })
          .locator("..")
          .getByRole("checkbox")
          .first()
          .check();
      }
      await adaPage.getByRole("button", { name: "Create facility" }).click();
      await expect(adaPage).toHaveURL(/\/facilities\/[^/]+/);
      await shot(adaPage, testInfo, "part3-02-ada-facility");
    } finally {
      await adaCtx.close();
    }

    const { context: boCtx, page: boPage } = await newVisitor(browser);
    try {
      await pasteToken(boPage, bo.token, bo.name);
      await boPage.goto("/settings/members");
      await expect(
        boPage.getByRole("heading", { name: "Members" }),
      ).toBeVisible();
      await expect(boPage.getByText("Ada", { exact: false })).toBeVisible();
      await expect(
        boPage.getByText("Ada's workshop floor", { exact: false }),
      ).toBeVisible();
      await expect(boPage.getByText(street)).toHaveCount(0);
      await shot(boPage, testInfo, "part3-03-bo-members");
    } finally {
      await boCtx.close();
    }
  });

  test("Bo does not see Ada's private design", async ({ browser }, testInfo) => {
    const ada = await requirePerson("ada");
    const bo = await requirePerson("bo");
    const designId = crypto.randomUUID();
    const manifest = {
      okhv: "1.0",
      id: designId,
      title: "Ada private bracket",
      version: "1.0.0",
      license: { hardware: "MIT" },
      licensor: "Ada",
      documentation_language: "en",
      function: "Holds things",
      manufacturing_processes: ["Assembly"],
    };

    const { context: adaCtx, page: adaPage } = await newVisitor(browser);
    try {
      await pasteToken(adaPage, ada.token, ada.name);
      await adaPage.goto("/okh/new");
      await adaPage
        .getByLabel("JSON")
        .fill(JSON.stringify(manifest, null, 2));
      // Clear any organisation the picker preselected.
      const onBehalf = adaPage.getByLabel("On behalf of");
      if (await onBehalf.count()) {
        await onBehalf.selectOption({ label: "None" });
      }
      await adaPage.getByRole("button", { name: "Create" }).click();
      await expect(adaPage).toHaveURL(new RegExp(`/okh/${designId}`));
      const designs = {
        ...(loadWorld().designs ?? {}),
        adaPrivate: designId,
      };
      saveWorld({ designs });
      await shot(adaPage, testInfo, "part3-04-ada-private-design");
    } finally {
      await adaCtx.close();
    }

    const { context: boCtx, page: boPage } = await newVisitor(browser);
    try {
      await pasteToken(boPage, bo.token, bo.name);
      await boPage.goto("/okh");
      await expect(
        boPage.getByText("Ada private bracket", { exact: true }),
      ).toHaveCount(0);
      await boPage.goto(`/okh/${designId}`);
      // A private design answers not found for someone else.
      await expect(
        boPage.getByText(/not found|does not exist|404/i).first(),
      ).toBeVisible();
      await shot(boPage, testInfo, "part3-05-bo-cannot-see-private");
    } finally {
      await boCtx.close();
    }
  });

  test("Bo mints and revokes an invite, and cannot set registration", async ({
    browser,
  }, testInfo) => {
    const bo = await requirePerson("bo");
    const { context, page } = await newVisitor(browser);
    try {
      await pasteToken(page, bo.token, bo.name);
      await page.goto("/settings/invites");
      await page.getByLabel("Expires in days").fill("7");
      await page.getByLabel("Use limit").fill("1");
      await page.getByRole("button", { name: "Mint invite" }).click();
      await expect(page.getByText(/\/register\?invite=/)).toBeVisible();
      await page.getByRole("button", { name: "Revoke" }).first().click();
      await expect(page.getByText("Revoked").first()).toBeVisible();
      await shot(page, testInfo, "part3-06-bo-invite");
    } finally {
      await context.close();
    }

    await expect(
      ohm(bo.token, ["identity", "registration", "--set", "closed"]),
    ).rejects.toBeInstanceOf(OhmError);
  });

  test("Chi's account page lists only Chi's keys", async ({
    browser,
  }, testInfo) => {
    // Assertion 3 from the proposal. Chi registered in part 2 with a password.
    const { context, page } = await newVisitor(browser);
    try {
      await page.goto("/login");
      await page.getByLabel("Username").fill("chi");
      await page.getByLabel("Password").fill("chi-passphrase-for-uat");
      await page.getByRole("button", { name: "Sign in" }).click();
      await page.goto("/account");
      // A leaked admin key list named other people. Chi must not see Renew or
      // Revoke on anyone else's key, and the page must not name Ada or Bo.
      await expect(page.getByText("Ada", { exact: true })).toHaveCount(0);
      await expect(page.getByText("Bo", { exact: true })).toHaveCount(0);
      await expect(page.getByText("Mitra", { exact: false })).toHaveCount(0);
      await shot(page, testInfo, "part3-07-chi-keys");
    } finally {
      await context.close();
    }
  });

  test("admin mint shows a token once and that token authenticates", async ({
    browser,
  }, testInfo) => {
    // Assertion 4. Create the account with the CLI, mint the identity through
    // the UI so the one-time panel is exercised, then authenticate with it.
    const operator = await requireOperator();
    const account = await ohm(operator.token, [
      "identity",
      "accounts",
      "create",
      "--name",
      "Dee",
    ]);
    const deeAccountId = field(account, "id");

    const { context, page } = await newVisitor(browser);
    try {
      await pasteToken(page, operator.token, operator.name);
      await page.goto("/settings/identities");
      await expect(
        page.getByRole("heading", { name: "Mint identity" }),
      ).toBeVisible();
      await page.getByLabel("Account").selectOption(deeAccountId);
      await page.getByLabel("Display name").fill("Dee");
      await page.getByRole("button", { name: /^Mint$/ }).click();
      const tokenPanel = page.getByRole("group").filter({
        has: page.locator("pre"),
      });
      await expect(tokenPanel).toBeVisible();
      const token = (await tokenPanel.locator("pre").innerText()).trim();
      expect(token.length).toBeGreaterThan(16);
      await shot(page, testInfo, "part3-08-admin-mint-token");
      const who = await ohm(token, ["identity", "whoami"]);
      expect(String(who.subject_did)).toMatch(/^did:key:/);
      expect(who.permissions).toEqual(
        expect.arrayContaining(["read", "write"]),
      );
    } finally {
      await context.close();
    }
  });
});


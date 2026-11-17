import { test, expect } from "@playwright/test";
import { api, apiOk } from "./api";
import { field, ohm } from "./ohm";
import { newVisitor, pasteToken } from "./people";
import { shot } from "./shot";
import {
  loadWorld,
  requireOperator,
  requirePerson,
  saveWorld,
} from "./world";

/**
 * Part 4 of the membership runbook: publish for an organisation (#577, #578).
 */
test.describe("@membership part 4: publish for an organisation", () => {
  test.describe.configure({ mode: "serial" });

  test("claim Field org and affiliate Ada", async () => {
    const operator = await requireOperator();
    const ada = await requirePerson("ada");
    if (loadWorld().spaceDid) {
      return;
    }
    const account = await ohm(operator.token, [
      "identity",
      "accounts",
      "create",
      "--name",
      "Field org",
      "--kind",
      "space",
    ]);
    const spaceAccountId = field(account, "id");
    const identity = await ohm(operator.token, [
      "identity",
      "identities",
      "create",
      "--account-id",
      spaceAccountId,
      "--kind",
      "space",
      "--name",
      "Field org",
    ]);
    const spaceDid = field(identity, "did");
    await ohm(operator.token, [
      "identity",
      "spaces",
      "claim",
      "--space-did",
      spaceDid,
      "--admin-did",
      operator.did,
    ]);
    const grant = await ohm(operator.token, [
      "identity",
      "affiliate",
      "add",
      ada.did,
      "--space",
      spaceDid,
    ]);
    const expires = field(grant, "expires_at");
    const days =
      (Date.parse(expires) - Date.now()) / (1000 * 60 * 60 * 24);
    expect(days, "affiliation lasts about 90 days in peacetime").toBeGreaterThan(
      80,
    );
    expect(days).toBeLessThan(100);
    saveWorld({ spaceDid });
  });

  test("Settings → Organisations lists Ada with Renew and Unaffiliate", async ({
    browser,
  }, testInfo) => {
    const operator = await requireOperator();
    const { context, page } = await newVisitor(browser);
    try {
      await pasteToken(page, operator.token, operator.name);
      await page.goto("/settings/organisations");
      await expect(page.getByText("Field org")).toBeVisible();
      await expect(page.getByText("Ada", { exact: false })).toBeVisible();
      await expect(page.getByRole("button", { name: "Renew" })).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Unaffiliate" }),
      ).toBeVisible();
      await shot(page, testInfo, "part4-01-organisations");
    } finally {
      await context.close();
    }
  });

  test("Ada saves Field pump on behalf of the organisation", async ({
    browser,
  }, testInfo) => {
    const ada = await requirePerson("ada");
    const spaceDid = loadWorld().spaceDid;
    expect(spaceDid).toBeTruthy();
    const designId = crypto.randomUUID();
    const manifest = {
      okhv: "1.0",
      id: designId,
      title: "Field pump",
      version: "1.0.0",
      license: { hardware: "MIT" },
      licensor: "Ada",
      documentation_language: "en",
      function: "Moves water",
      manufacturing_processes: ["Assembly"],
    };

    const { context, page } = await newVisitor(browser);
    try {
      await pasteToken(page, ada.token, ada.name);
      await page.goto("/okh/new");
      const onBehalf = page.getByLabel("On behalf of");
      await expect(onBehalf).toBeVisible();
      // The picker has the organisation selected, and None is available.
      await expect(onBehalf.locator("option", { hasText: "None" })).toHaveCount(
        1,
      );
      if (!spaceDid) {
        throw new Error("spaceDid missing");
      }
      await onBehalf.selectOption(spaceDid);
      await page.getByLabel("JSON").fill(JSON.stringify(manifest, null, 2));
      await page.getByRole("button", { name: "Create" }).click();
      await expect(page).toHaveURL(new RegExp(`/okh/${designId}`));
      await expect(
        page.getByRole("heading", { name: "Authorship" }),
      ).toBeVisible();
      await expect(page.getByText(spaceDid, { exact: false })).toBeVisible();
      // The design content itself must not contain the space DID.
      const stored = await apiOk(ada.token, "GET", `/api/okh/${designId}`);
      const body = JSON.stringify(stored);
      expect(body).not.toContain(spaceDid);
      const designs = {
        ...(loadWorld().designs ?? {}),
        fieldPump: designId,
      };
      saveWorld({ designs });
      await shot(page, testInfo, "part4-02-field-pump");
    } finally {
      await context.close();
    }
  });

  test("Ada saves an unaffiliated design", async ({ browser }, testInfo) => {
    const ada = await requirePerson("ada");
    const designId = crypto.randomUUID();
    const manifest = {
      okhv: "1.0",
      id: designId,
      title: "Field pump, unaffiliated",
      version: "1.0.0",
      license: { hardware: "MIT" },
      licensor: "Ada",
      documentation_language: "en",
      function: "Moves water",
      manufacturing_processes: ["Assembly"],
    };

    const { context, page } = await newVisitor(browser);
    try {
      await pasteToken(page, ada.token, ada.name);
      await page.goto("/okh/new");
      await page.getByLabel("On behalf of").selectOption({ label: "None" });
      await page.getByLabel("JSON").fill(JSON.stringify(manifest, null, 2));
      await page.getByRole("button", { name: "Create" }).click();
      await expect(page).toHaveURL(new RegExp(`/okh/${designId}`));
      // No organisation on authorship.
      await expect(page.getByText(/^On behalf of$/)).toHaveCount(0);
      const designs = {
        ...(loadWorld().designs ?? {}),
        unaffiliated: designId,
      };
      saveWorld({ designs });
      await shot(page, testInfo, "part4-03-unaffiliated");
    } finally {
      await context.close();
    }
  });

  test("a stranger's space DID is refused and stores nothing", async () => {
    const ada = await requirePerson("ada");
    const designId = crypto.randomUUID();
    const result = await api(
      ada.token,
      "POST",
      "/api/okh/create?on_behalf_of=did:key:zNotHers",
      {
        content: {
          okhv: "1.0",
          id: designId,
          title: "x",
          version: "1.0.0",
          license: { hardware: "MIT" },
          licensor: "Ada",
          documentation_language: "en",
          function: "x",
          manufacturing_processes: ["Assembly"],
        },
      },
    );
    expect(result.status).toBeGreaterThanOrEqual(400);
    expect(result.status).toBeLessThan(500);
    const get = await api(ada.token, "GET", `/api/okh/${designId}`);
    expect(get.status).toBe(404);
  });
});

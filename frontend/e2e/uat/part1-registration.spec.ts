import { test, expect, type Page } from "@playwright/test";
import { NODE_NAME, OPERATOR_NAME } from "./env";
import { field, ohm } from "./ohm";
import { newVisitor } from "./people";
import { shot } from "./shot";
import { requireOperator } from "./world";

/**
 * Part 1 of the membership runbook: who may register (#568).
 *
 * One browser context is used for the whole part, on purpose. The registration
 * page keeps what the node last said about registration, and the order
 * open, closed, open in a context that has already seen the form is what
 * catches a page that keeps showing the form after the node has closed.
 */
test.describe("@membership part 1: who may register", () => {
  test.describe.configure({ mode: "serial" });

  const FORM = "Create an identity on this node";
  const CLOSED = "This node does not accept registrations";

  async function setRegistration(token: string, mode: "open" | "closed") {
    const result = await ohm(token, [
      "identity",
      "registration",
      "--set",
      mode,
    ]);
    expect(field(result, "registration")).toBe(mode);
  }

  async function expectForm(page: Page) {
    await expect(page.getByRole("heading", { name: FORM })).toBeVisible();
    await expect(page.getByLabel("Username")).toBeVisible();
  }

  test("closed shows no form, open shows it again", async ({
    browser,
  }, testInfo) => {
    const operator = await requireOperator();
    const { context, page } = await newVisitor(browser);
    try {
      await setRegistration(operator.token, "open");
      await page.goto("/register");
      await expectForm(page);

      await setRegistration(operator.token, "closed");
      await test.step("the page says this node does not accept registrations. There is no form", async () => {
        await page.reload();
        await expect(page.getByText(CLOSED, { exact: true })).toBeVisible();
        await expect(page.getByRole("heading", { name: FORM })).toHaveCount(0);
        await expect(page.getByLabel("Username")).toHaveCount(0);
        await expect(
          page.getByRole("button", { name: "Register" }),
        ).toHaveCount(0);
        await shot(page, testInfo, "part1-01-registration-closed");
      });

      await setRegistration(operator.token, "open");
      await test.step("the form is there, with no invite in the address. It names the node and its operator", async () => {
        await page.reload();
        await expectForm(page);
        // The app adds its own theme parameters, so "no invite" is the claim,
        // not "no query string".
        expect(new URL(page.url()).searchParams.has("invite")).toBe(false);
        await expect(page.getByText(NODE_NAME, { exact: true })).toBeVisible();
        await expect(
          page.getByText(OPERATOR_NAME, { exact: true }),
        ).toBeVisible();
        await shot(page, testInfo, "part1-02-registration-open");
      });
    } finally {
      await context.close();
    }
  });
});

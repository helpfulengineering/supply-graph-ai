import {
  expect,
  type Browser,
  type BrowserContext,
  type Page,
} from "@playwright/test";

/**
 * A person is a browser context: its own cookies and its own session storage,
 * which is what "a private window per person" means in the runbook.
 *
 * A token goes in through the page a real person would use, Settings → Session.
 * Writing it into storage would skip the very form the runbook asks a person to
 * use, and a regression in that form would then pass.
 */
export interface Visitor {
  context: BrowserContext;
  page: Page;
}

export async function newVisitor(browser: Browser): Promise<Visitor> {
  const context = await browser.newContext();
  const page = await context.newPage();
  return { context, page };
}

/** Paste a token at /settings/session and wait until the node has accepted it. */
export async function pasteToken(
  page: Page,
  token: string,
  expectedName: string,
): Promise<void> {
  await page.goto("/settings/session");
  await page.getByLabel("Token").fill(token);
  await page.getByRole("button", { name: "Save" }).click();
  const identity = page.getByRole("region", { name: "Current identity" });
  await expect(identity.getByText(expectedName, { exact: true })).toBeVisible();
}

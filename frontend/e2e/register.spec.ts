import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

/**
 * Registration is what stops one node being structurally special: a visitor
 * can become someone here without the operator. These cover the journey the
 * UI is responsible for — sign up, land signed in, find what only you can see
 * — and the boundary that a non-admin does not thereby gain Settings.
 */

const NON_ADMIN_WHOAMI = {
  key_id: "00000000-0000-0000-0000-0000000000cd",
  name: "Ada Lovelace",
  permissions: ["read", "write"],
  account_id: "00000000-0000-0000-0000-0000000000cc",
  subject_did: "did:key:zAdaRegistered",
};

test("a visitor registers and lands signed in", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked identity APIs only");
  await page.goto("/register");

  await expect(
    page.getByRole("heading", { name: "Create an identity on this node" }),
  ).toBeVisible();
  await page.getByLabel("Display name").fill("Ada Lovelace");
  await page.getByRole("button", { name: "Register" }).click();

  // Shown once for keeping — and already the session, so there is no second
  // paste step.
  await expect(page.getByText("ohm_registered_once")).toBeVisible();
  await expect(page.getByRole("heading", { name: "You are signed in" })).toBeVisible();
  // A session the app minted persists (#415), so it is in localStorage and not
  // in sessionStorage — never both, or signing out of one would leave the
  // other holding a live credential.
  expect(
    await page.evaluate(() => localStorage.getItem("ohm_api_key")),
  ).toBe("ohm_registered_once");
  expect(
    await page.evaluate(() => sessionStorage.getItem("ohm_api_key")),
  ).toBeNull();

  await expectNoA11yViolations(page);
});

test("a registered visitor is still signed in after reopening the tab", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked identity APIs only");
  await page.route("**/v1/api/identity/whoami", (route) =>
    route.fulfill({ json: NON_ADMIN_WHOAMI }),
  );
  await page.goto("/register");
  await page.getByLabel("Display name").fill("Ada Lovelace");
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.getByText("ohm_registered_once")).toBeVisible();

  // A new page in the same context is a new tab: sessionStorage does not carry
  // over, localStorage does. This is the whole point of the change.
  const reopened = await page.context().newPage();
  await reopened.route("**/v1/api/identity/whoami", (route) =>
    route.fulfill({ json: NON_ADMIN_WHOAMI }),
  );
  await reopened.goto("/account");

  await expect(
    reopened.getByRole("link", { name: "Ada Lovelace" }),
  ).toBeVisible();
  await expect(
    reopened.getByText(/stay signed in on this device/),
  ).toBeVisible();
  await reopened.close();
});

test("a pasted key is still gone when the tab closes", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked identity APIs only");
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "pasted-admin-token");
  });
  await page.goto("/account");

  // The posture chosen for an operator pasting an admin key is unchanged: it
  // must never reach persistent storage.
  expect(
    await page.evaluate(() => localStorage.getItem("ohm_api_key")),
  ).toBeNull();
  await expect(page.getByText(/signed in for this tab only/)).toBeVisible();
});

test("registration is not offered when the node has it closed", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked identity APIs only");
  await page.route("**/v1/api/identity/security-policy", (route) =>
    route.fulfill({ json: { mode: "shielded", open_registration: false } }),
  );
  await page.goto("/register");

  await expect(
    page.getByText("This node does not accept registrations"),
  ).toBeVisible();
  await expect(page.getByLabel("Display name")).toHaveCount(0);
});

test("a registered non-admin gets an account page but no Settings", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked identity APIs only");
  await page.route("**/v1/api/identity/whoami", (route) =>
    route.fulfill({ json: NON_ADMIN_WHOAMI }),
  );
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "non-admin-token");
  });
  await page.goto("/account");

  // The session is visible in the chrome, which is what a non-admin lacked.
  await expect(
    page.getByRole("link", { name: "Ada Lovelace" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Identity" })).toBeVisible();

  // Settings stays admin-only. The guard is unchanged; this asserts that
  // registering did not quietly widen it.
  await page.getByRole("button", { name: "Site menu" }).click();
  await expect(page.getByRole("link", { name: "Keys & accounts" })).toHaveCount(0);
  await page.getByRole("button", { name: "Close menu" }).click();

  await expectNoA11yViolations(page);
});

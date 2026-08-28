import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

test("settings session is reachable without an admin key (paste bootstrap)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked whoami only");
  await page.goto("/settings/session");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "API key" })).toBeVisible();
  // The account entry lives in the hamburger sitemap and reads "Connect"
  // when no API key is present — the paste-bootstrap affordance.
  await page.getByRole("button", { name: "Site menu" }).click();
  await expect(page.getByRole("link", { name: /Connect/ })).toBeVisible();
  await page.getByRole("button", { name: "Close menu" }).click();
  await expect(page.getByRole("link", { name: "Keys & accounts" })).toHaveCount(
    0,
  );
});

test("settings session a11y with mocked admin whoami", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked whoami only");
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });
  await page.goto("/settings/session");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "API key" })).toBeVisible();
  // With an admin whoami the sitemap's account entry reads "Settings".
  await page.getByRole("button", { name: "Site menu" }).click();
  await expect(page.getByRole("link", { name: /^Settings/ })).toBeVisible();
  await page.getByRole("button", { name: "Close menu" }).click();
  await expectNoA11yViolations(page);
});

test("settings identities / grants / spaces tabs (F3)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked identity APIs only");
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });

  await page.goto("/settings/identities");
  await expect(
    page.getByRole("heading", { name: "Mint identity" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Identities" })).toBeVisible();
  await expectNoA11yViolations(page);

  // Every /settings/* route renders the same SettingsPage, which picks its
  // panel from usePathname(). Between the click and the route committing,
  // that hook still returns the OLD path, so the previous tab's panel is
  // what is on screen — asserting the new panel without waiting for the URL
  // races the transition. It loses often enough to fail this spec on the
  // contributor's own tree (2 of 3 full-suite runs, dev server).
  await page.getByRole("link", { name: "Grants" }).click();
  await page.waitForURL(/\/settings\/grants(\?|$)/);
  await expect(
    page.getByRole("heading", { name: "List grants" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Bootstrap edge grant" }),
  ).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Spaces" }).click();
  await page.waitForURL(/\/settings\/spaces(\?|$)/);
  await expect(
    page.getByRole("heading", { name: "Claim space" }),
  ).toBeVisible();
  await expect(page.getByText(/did:key:z6MktestSpace/)).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Reputation" }).click();
  await page.waitForURL(/\/settings\/reputation(\?|$)/);
  await expect(
    page.getByRole("heading", { name: "Reputation lookup" }),
  ).toBeVisible();
  await page
    .getByLabel("Subject DID")
    .fill("did:key:z6MktestPerson0000000000000000000000001");
  await page.getByRole("button", { name: "Look up" }).click();
  await expect(page.getByText("certified")).toBeVisible();
  await expect(page.getByText("domain_bound")).toBeVisible();
  await expect(page.getByText("vouch")).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Bindings" }).click();
  await expect(
    page.getByRole("heading", { name: "Domain bind" }),
  ).toBeVisible();
  await expect(page.getByText("oauth:github:octocat")).toBeVisible();
  await page
    .getByLabel("Subject DID")
    .first()
    .fill("did:key:z6MktestPerson0000000000000000000000001");
  await page.getByRole("textbox", { name: "Domain" }).fill("example.org");
  await page.getByRole("button", { name: "Start" }).click();
  await expect(
    page.getByText("https://example.org/.well-known/ohm-did.json"),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy JSON" })).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Directory" }).click();
  await expect(
    page.getByRole("heading", { name: "Directory", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("https://ohm.example.org")).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Federation" }).click();
  await expect(
    page.getByRole("heading", { name: "Node status" }),
  ).toBeVisible();
  await expect(page.getByText("Peer B")).toBeVisible();
  await page.getByRole("button", { name: "Sync", exact: true }).click();
  await expect(page.getByText(/Sync finished/)).toBeVisible();
  await expectNoA11yViolations(page);
});

test("matching rules: compare before import", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked whoami only");
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });
  await page.goto("/settings/matching");

  await expect(
    page.getByRole("heading", { name: "Capability rules" }),
  ).toBeVisible();
  // The loaded set reads as a sentence about what each rule does, not as ids.
  await expect(
    page.getByText("cnc_milling satisfies machining, milling"),
  ).toBeVisible();

  // Import is unreachable until the file has been checked: the whole point of
  // the step is that nobody writes a file they have not seen the effect of.
  const importButton = page.getByRole("button", { name: "Import" });
  await expect(importButton).toBeDisabled();

  await page
    .getByLabel("Check a rules file")
    .fill("domain: manufacturing\nrules: []\n");
  // exact, or "Check" also matches "Check processes" and "Check file types".
  await page.getByRole("button", { name: "Check", exact: true }).click();

  // Twice on the page by design: the terse summary beside the button, and the
  // sentence that spells out which domains it lands in.
  await expect(page.getByText("1 new · 1 changed").first()).toBeVisible();
  await expect(importButton).toBeEnabled();

  await expectNoA11yViolations(page);
});

test("matching rules: reset is behind a typed confirmation", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked whoami only");
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });
  await page.goto("/settings/matching");

  const resetButton = page.getByRole("button", { name: "Reset rules" });
  await expect(resetButton).toBeDisabled();
  await page.getByLabel("Type reset to confirm").fill("reset");
  await expect(resetButton).toBeEnabled();
});

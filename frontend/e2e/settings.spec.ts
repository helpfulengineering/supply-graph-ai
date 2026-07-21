import { test, expect } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

test("settings session is reachable without an admin key (paste bootstrap)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked whoami only");
  await page.goto("/settings/session");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "API key" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Connect" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Keys & accounts" })).toHaveCount(0);
});

test("settings session a11y with mocked admin whoami", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked whoami only");
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });
  await page.goto("/settings/session");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "API key" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Settings" })).toBeVisible();
  await expectNoA11yViolations(page);
});

test("settings identities / grants / spaces tabs (F3)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked identity APIs only");
  await page.addInitScript(() => {
    sessionStorage.setItem("ohm_api_key", "test-admin-token");
  });

  await page.goto("/settings/identities");
  await expect(page.getByRole("heading", { name: "Mint identity" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Identities" })).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Grants" }).click();
  await expect(page.getByRole("heading", { name: "List grants" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Bootstrap edge grant" })).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Spaces" }).click();
  await expect(page.getByRole("heading", { name: "Claim space" })).toBeVisible();
  await expect(page.getByText(/did:key:z6MktestSpace/)).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Reputation" }).click();
  await expect(page.getByRole("heading", { name: "Reputation lookup" })).toBeVisible();
  await page.getByLabel("Subject DID").fill("did:key:z6MktestPerson0000000000000000000000001");
  await page.getByRole("button", { name: "Look up" }).click();
  await expect(page.getByText("certified")).toBeVisible();
  await expect(page.getByText("domain_bound")).toBeVisible();
  await expect(page.getByText("vouch")).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Bindings" }).click();
  await expect(page.getByRole("heading", { name: "Domain bind" })).toBeVisible();
  await expect(page.getByText("oauth:github:octocat")).toBeVisible();
  await page.getByLabel("Subject DID").first().fill(
    "did:key:z6MktestPerson0000000000000000000000001",
  );
  await page.getByRole("textbox", { name: "Domain" }).fill("example.org");
  await page.getByRole("button", { name: "Start" }).click();
  await expect(page.getByText("https://example.org/.well-known/ohm-did.json")).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy JSON" })).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Directory" }).click();
  await expect(page.getByRole("heading", { name: "Directory", exact: true })).toBeVisible();
  await expect(page.getByText("https://ohm.example.org")).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByRole("link", { name: "Federation" }).click();
  await expect(page.getByRole("heading", { name: "Node status" })).toBeVisible();
  await expect(page.getByText("Peer B")).toBeVisible();
  await page.getByRole("button", { name: "Sync", exact: true }).click();
  await expect(page.getByText(/Sync finished/)).toBeVisible();
  await expectNoA11yViolations(page);
});

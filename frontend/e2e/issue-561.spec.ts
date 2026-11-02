import { readFile } from "node:fs/promises";
import type { Page } from "@playwright/test";
import { test, expect } from "./mock-api";

/**
 * Acceptance: #561, a first-time designer adding an electronics design.
 *
 * Each test is one thing the reporter hit, in the order they hit it, written as
 * what they should have seen. Each is marked `test.fail` with the sub-issue
 * that fixes it: Playwright fails the run if a marked test passes, so the fix
 * PR has to delete the marker. Generation quality itself (schematic, version,
 * BOM, processes) is covered on the backend in
 * `tests/integration/test_issue_561_first_contact.py`.
 */

const REPO = "https://github.com/mitra42/frugal-iot-hw-sensor";

const GENERATED = {
  title: "Frugal IoT sensor board",
  version: "",
  function: "ESP32 sensor board for the Frugal IoT stack",
  documentation_language: "en",
  licensor: { name: "Mitra Ardron" },
  license: { hardware: "CERN-OHL-S-2.0" },
  manufacturing_processes: ["PCB Fabrication", "Sheet Metal Forming"],
  manufacturing_specs: {
    process_requirements: [
      { process_name: "PCB Fabrication" },
      { process_name: "Sheet Metal Forming" },
    ],
  },
  tsdc: ["PCB", "SHEET"],
  bom: {
    name: "Frugal IoT sensor board BOM",
    external_file: "BOM.csv",
    summary: { total_components: 4 },
  },
};

function signIn(page: Page) {
  return page.addInitScript(() =>
    localStorage.setItem("ohm_api_key", "ohm_signed_in"),
  );
}

/** Submit answers once; the single poll returns `GENERATED`. */
async function mockGeneration(page: Page) {
  await page.route("**/api/okh/generate-from-url/jobs", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({
          status: 202,
          json: { batch_id: "b-561", jobs: [{ job_id: "j-561", url: REPO }] },
        })
      : route.fallback(),
  );
  await page.route("**/api/okh/generate-from-url/jobs/j-561", (route) =>
    route.fulfill({
      json: {
        job_id: "j-561",
        state: "SUCCESS",
        fraction: 1,
        url: REPO,
        manifest: GENERATED,
        quality_report: { missing_required_fields: [] },
      },
    }),
  );
}

/** Generate, then do what the reporter would: enter the version they know. */
async function generate(page: Page) {
  await page.goto("/okh/generate");
  await page.getByLabel(/Repository URL/i).fill(REPO);
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByLabel("Title")).toHaveValue(GENERATED.title);
  await page.getByLabel("Version").fill("0.2");
}

/**
 * Assert before acting on anything a fix has yet to build. A click on a missing
 * element waits out the test timeout, and Playwright reports a timeout as
 * unexpected even under `test.fail`.
 */
async function present(locator: import("@playwright/test").Locator) {
  await expect(locator).toBeVisible();
  return locator;
}

// eslint-disable-next-line no-empty-pattern -- Playwright requires the destructuring form here, and this hook needs no fixture.
test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "mocked journey");
});

test("the landing page offers adding a design, not only finding one", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: /add your design/i }),
  ).toHaveAttribute("href", /\/okh\/generate/);
});

test("LLM generation without an account says to register, in plain words", async ({
  page,
}) => {
  await page.route("**/api/okh/generate-from-url/jobs", (route) =>
    route.fulfill({
      status: 401,
      json: {
        detail:
          "LLM-enabled generation requires authentication. " +
          "Pass Authorization: Bearer <token>, or set no_llm=true.",
      },
    }),
  );
  await page.goto("/okh/generate");
  await page.getByLabel(/Repository URL/i).fill(REPO);
  await page.getByRole("button", { name: "Generate" }).click();

  const alert = page.getByRole("alert");
  await expect(alert).toContainText(/account/i);
  await expect(alert).not.toContainText("Authorization");
  await expect(alert.getByRole("link", { name: /register/i })).toBeVisible();
  await expect(alert.getByRole("link", { name: /sign in/i })).toBeVisible();
  await expect(
    alert.getByRole("button", { name: /without the language model/i }),
  ).toBeVisible();
});

test("a process removed in the editor is gone from the downloaded YAML", async ({
  page,
}) => {
  // Stands in for the node's derivation, which the backend suite covers; what
  // this checks is that the editor applies it before anything leaves.
  await page.route("**/api/okh/normalize", async (route) => {
    const { content } = route.request().postDataJSON();
    const names: string[] = content.manufacturing_processes;
    await route.fulfill({
      json: {
        content: {
          ...content,
          manufacturing_specs: {
            process_requirements: names.map((process_name) => ({ process_name })),
          },
          tsdc: names.includes("PCB Fabrication") ? ["PCB"] : [],
        },
      },
    });
  });
  await mockGeneration(page);
  await generate(page);

  await page.getByRole("button", { name: "Remove Sheet Metal Forming" }).click();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download YAML" }).click(),
  ]);
  const yaml = await readFile((await download.path())!, "utf8");
  expect(yaml).toContain("PCB Fabrication");
  expect(yaml).not.toContain("Sheet Metal Forming");
  expect(yaml).not.toMatch(/-\s*SHEET\b/);
});

test("the editor says what the BOM is and which file it came from", async ({
  page,
}) => {
  await mockGeneration(page);
  await generate(page);

  const bom = page.getByRole("group", { name: /bill of materials/i });
  await expect(bom).toContainText("BOM.csv");
  await expect(bom).toContainText(/parts/i);
});

test("a signed-in designer saves the generated design to this node", async ({
  page,
}) => {
  test.fail(true, "#566: Generate can only download");
  await signIn(page);
  await mockGeneration(page);
  let saved: Record<string, unknown> | null = null;
  await page.route("**/api/okh/create", async (route) => {
    saved = route.request().postDataJSON();
    return route.fulfill({
      status: 201,
      json: { okh: { id: "11111111-2222-3333-4444-555555555561" } },
    });
  });
  await generate(page);

  await (
    await present(page.getByRole("button", { name: /save to this node/i }))
  ).click();
  await expect(page).toHaveURL(/\/okh\/11111111-2222-3333-4444-555555555561/);
  expect(saved).not.toBeNull();
});

test("an anonymous designer is offered sign-in to save, and keeps their edits", async ({
  page,
}) => {
  test.fail(true, "#572: registering means leaving Generate and starting over");
  await mockGeneration(page);
  await generate(page);
  await page.getByLabel("Title").fill("Frugal IoT sensor v0.2");

  await (
    await present(page.getByRole("button", { name: /sign in to save/i }))
  ).click();
  const signup = page.getByRole("dialog");
  await (await present(signup.getByLabel("Username"))).fill("mitra");
  await signup.getByLabel("Password", { exact: true }).fill("correct horse");
  await signup.getByLabel("Display name").fill("Mitra");
  await signup.getByRole("button", { name: /create account/i }).click();

  await expect(page.getByLabel("Title")).toHaveValue("Frugal IoT sensor v0.2");
  await expect(
    page.getByRole("button", { name: /save to this node/i }),
  ).toBeVisible();
});

test("signing up leaves one thing to keep: a recovery code", async ({
  page,
}) => {
  test.fail(true, "#571: signup shows an API token and a recovery code");
  await page.goto("/register");
  await expect(page.getByText(/key pair/i)).toHaveCount(0);
  await (await present(page.getByLabel("Username"))).fill("mitra");
  await page.getByLabel("Password", { exact: true }).fill("correct horse");
  await page.getByLabel("Display name").fill("Mitra");
  await page.getByRole("button", { name: /create account|register/i }).click();

  await expect(page.getByText(/recovery code/i).first()).toBeVisible();
  await expect(page.getByText("ohm_registered_once")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /download/i })).toBeVisible();
  const proceed = page.getByRole("button", { name: /continue/i });
  await expect(proceed).toBeDisabled();
  await page.getByRole("checkbox", { name: /saved/i }).check();
  await expect(proceed).toBeEnabled();
});

test("a member signs in with a username and password", async ({ page }) => {
  await page.goto("/register");
  await (await present(page.getByRole("link", { name: /^sign in$/i }))).click();
  await expect(page.getByLabel("Username")).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(page.getByLabel(/api key|token/i)).toHaveCount(0);
});

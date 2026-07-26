import { test, expect } from "./mock-api";

// Slice A + B: generate an OKH manifest from a repository URL, then review it
// through the guided tiered editor. The mocked lane owns the behaviour; the
// real-api lane would need a live repository read (up to a minute) and a shared
// token quota, so it only checks the page loads.

const MANIFEST = {
  title: "Open Source Rover",
  version: "1.0.0",
  function: "",
  documentation_language: "en",
  licensor: { name: "JPL" },
  license: { hardware: "Apache-2.0" },
  manufacturing_processes: ["3D Printing", "Laser Cutting"],
  materials: [{ name: "PLA" }],
  stray_field: "kept",
};

async function mockGenerate(page: import("@playwright/test").Page, body: unknown, status = 200) {
  await page.route("**/api/okh/generate-from-url", (route) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    }),
  );
}

test("page loads", async ({ page }) => {
  await page.goto("/okh/generate");
  await expect(
    page.getByRole("heading", { name: /generate a design from a url/i }),
  ).toBeVisible();
});

test("rejects an unsupported host before calling the API (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts client-side validation");
  let called = false;
  await page.route("**/api/okh/generate-from-url", (route) => {
    called = true;
    return route.fulfill({ status: 200, body: "{}" });
  });

  await page.goto("/okh/generate");
  await page.getByLabel("Repository URL").fill("https://bitbucket.org/a/b");
  await page.getByRole("button", { name: "Generate" }).click();

  await expect(page.getByRole("alert")).toContainText(/only public github and gitlab/i);
  expect(called).toBe(false);
});

test("generates, then guides review of the result (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await mockGenerate(page, {
    success: true,
    message: "ok",
    manifest: MANIFEST,
    quality_report: {
      missing_required_fields: ["function"],
      recommendations: ["Add a description"],
    },
  });

  await page.goto("/okh/generate");
  await page.getByLabel("Repository URL").fill("https://github.com/nasa-jpl/rover");
  await page.getByRole("button", { name: "Generate" }).click();

  // Quality banner warns about the missing required field without blocking.
  await expect(page.getByText(/1 required field could not be extracted/i)).toBeVisible();
  await expect(page.getByText("Add a description")).toBeVisible();

  // Tier 1 is present and pre-filled from the extraction.
  await expect(page.getByLabel("Title")).toHaveValue("Open Source Rover");
  await expect(page.getByLabel("Licensor name")).toHaveValue("JPL");

  // Tier 2 list fields render as chips.
  await expect(page.getByRole("list", { name: "Manufacturing processes values" })).toContainText(
    "3D Printing",
  );

  // Both formats are offered, and both are gated until required fields are valid.
  const yaml = page.getByRole("button", { name: "Download YAML" });
  const json = page.getByRole("button", { name: "Download JSON" });
  await expect(yaml).toBeDisabled();
  await expect(json).toBeDisabled();
  await page.getByLabel("Function").fill("Drives around");
  await expect(yaml).toBeEnabled();
  await expect(json).toBeEnabled();
});

test("downloads the reviewed manifest as YAML (mocked)", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await mockGenerate(page, {
    success: true,
    message: "ok",
    manifest: { ...MANIFEST, function: "Drives around" },
    quality_report: { missing_required_fields: [] },
  });

  await page.goto("/okh/generate");
  await page.getByLabel("Repository URL").fill("https://github.com/nasa-jpl/rover");
  await page.getByRole("button", { name: "Generate" }).click();

  // Edits made during review must reach the downloaded file.
  await page.getByLabel("Title").fill("Renamed Rover");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download YAML" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("renamed-rover.okh.yaml");
});

test("explains a rate-limited generation in plain language (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts mocked failure");
  await mockGenerate(page, { detail: "Too Many Requests" }, 429);

  await page.goto("/okh/generate");
  await page.getByLabel("Repository URL").fill("https://github.com/a/b");
  await page.getByRole("button", { name: "Generate" }).click();

  const alert = page.getByRole("alert");
  await expect(alert).toContainText(/rate limit/i);
  await expect(alert).not.toContainText("429");
});

import { test, expect } from "./mock-api";

// Generate an OKH manifest from a repository URL via async jobs, review it
// through the guided tiered editor, then hand it to matching unsaved.

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

/** Mock submit + a multi-poll progression that ends in SUCCESS. */
async function mockGenerateJobs(
  page: import("@playwright/test").Page,
  opts: {
    manifest?: Record<string, unknown>;
    quality_report?: Record<string, unknown>;
    submitStatus?: number;
    submitBody?: unknown;
  } = {},
) {
  const jobId = "job-e2e-1";
  const url = "https://github.com/nasa-jpl/rover";
  let polls = 0;

  if (opts.submitStatus && opts.submitStatus >= 400) {
    await page.route("**/api/okh/generate-from-url/jobs", (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      return route.fulfill({
        status: opts.submitStatus,
        contentType: "application/json",
        body: JSON.stringify(opts.submitBody ?? { detail: "error" }),
      });
    });
    return;
  }

  await page.route("**/api/okh/generate-from-url/jobs", (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        batch_id: "batch-1",
        jobs: [{ job_id: jobId, url }],
      }),
    });
  });

  await page.route(`**/api/okh/generate-from-url/jobs/${jobId}`, (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    polls += 1;
    if (polls < 3) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          job_id: jobId,
          state: "PROGRESS",
          stage: polls === 1 ? "clone" : "nlp",
          fraction: polls === 1 ? 0.2 : 0.55,
          message: "working",
          url,
        }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: jobId,
        state: "SUCCESS",
        stage: null,
        fraction: 1,
        message: "ok",
        url,
        manifest: opts.manifest ?? MANIFEST,
        quality_report: opts.quality_report ?? {
          missing_required_fields: ["function"],
          recommendations: ["Add a description"],
        },
      }),
    });
  });

  await page.route(`**/api/okh/generate-from-url/jobs/${jobId}/revoke`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: jobId,
        state: "REVOKED",
        message: "Job cancelled",
      }),
    }),
  );
}

test("page loads", async ({ page }) => {
  await page.goto("/okh/generate");
  await expect(
    page.getByRole("heading", { name: /generate a design from a url/i }),
  ).toBeVisible();
});

test("real API: submit-then-poll completes with a progress bar", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "real-api", "live Compose API only");
  test.setTimeout(180_000);

  await page.goto("/okh/generate");
  await page
    .getByLabel(/Repository URL/i)
    .fill("https://github.com/blooop/Hello-World");
  await page.getByRole("button", { name: "Generate" }).click();

  await expect(page.getByRole("progressbar").first()).toBeVisible({
    timeout: 15_000,
  });
  // Heuristic-only path should finish well under the old 120s proxy ceiling.
  await expect(page.getByLabel("Title")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByRole("button", { name: "Download YAML" })).toBeVisible();
});

test("rejects an unsupported host before calling the API (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts client-side validation");
  let called = false;
  await page.route("**/api/okh/generate-from-url/jobs", (route) => {
    called = true;
    return route.fulfill({ status: 202, body: "{}" });
  });

  await page.goto("/okh/generate");
  await page.getByLabel(/Repository URL/i).fill("https://bitbucket.org/a/b");
  await page.getByRole("button", { name: "Generate" }).click();

  await expect(page.getByRole("alert")).toContainText(/only public github and gitlab/i);
  expect(called).toBe(false);
});

test("generates, then guides review of the result (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await mockGenerateJobs(page);

  await page.goto("/okh/generate");
  await page.getByLabel(/Repository URL/i).fill("https://github.com/nasa-jpl/rover");
  await page.getByRole("button", { name: "Generate" }).click();

  await expect(page.getByRole("progressbar").first()).toBeVisible();

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
  await mockGenerateJobs(page, {
    manifest: { ...MANIFEST, function: "Drives around" },
    quality_report: { missing_required_fields: [] },
  });

  await page.goto("/okh/generate");
  await page.getByLabel(/Repository URL/i).fill("https://github.com/nasa-jpl/rover");
  await page.getByRole("button", { name: "Generate" }).click();

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
  await mockGenerateJobs(page, {
    submitStatus: 429,
    submitBody: { detail: "Too Many Requests" },
  });

  await page.goto("/okh/generate");
  await page.getByLabel(/Repository URL/i).fill("https://github.com/a/b");
  await page.getByRole("button", { name: "Generate" }).click();

  const alert = page.getByRole("alert");
  await expect(alert).toContainText(/rate limit/i);
  await expect(alert).not.toContainText("429");
});

test("hands the reviewed design off to match without saving it (mocked)", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name === "real-api", "asserts fixture data");
  await mockGenerateJobs(page, {
    manifest: { ...MANIFEST, function: "Drives around" },
    quality_report: { missing_required_fields: [] },
  });

  let matchBody: Record<string, unknown> | null = null;
  await page.route("**/api/match", async (route) => {
    matchBody = JSON.parse(route.request().postData() ?? "{}");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: { solutions: [], total_solutions: 0 } }),
    });
  });

  await page.goto("/okh/generate");
  await page.getByLabel(/Repository URL/i).fill("https://github.com/nasa-jpl/rover");
  await page.getByRole("button", { name: "Generate" }).click();
  await page.getByRole("button", { name: "Find who can build this" }).click();

  await expect(page.getByText("Open Source Rover")).toBeVisible();
  await expect(page.getByText(/not been saved to the catalogue/i)).toBeVisible();

  await page.getByRole("button", { name: /Run Match/i }).click();
  await expect.poll(() => matchBody).not.toBeNull();
  expect(matchBody!.okh_manifest).toBeTruthy();
  expect(matchBody!.okh_id).toBeUndefined();
  expect(matchBody!.save_solution).toBe(false);
});

import { readFileSync } from "node:fs";
import { test } from "./mock-api";

// Captures a screenshot of each configured route into artifacts/screenshots so
// a human can review UI changes asynchronously without running anything. Runs
// only in the mocked lane (deterministic; no backend/data dependency).
const harness = JSON.parse(
  readFileSync(new URL("../harness.config.json", import.meta.url), "utf-8"),
) as { routesToScreenshot: string[] };

for (const route of harness.routesToScreenshot) {
  test(`screenshot ${route}`, async ({ page }) => {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    const slug = route === "/" ? "home" : route.replace(/^\//, "").replace(/\//g, "-");
    await page.screenshot({
      path: `artifacts/screenshots/${slug}.png`,
      fullPage: true,
    });
  });
}

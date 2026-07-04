import { test } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";

// Accessibility coverage across the v1 journeys (mocked lane — several routes
// need fixture ids). Catches contrast/label regressions the per-journey specs
// otherwise miss.
const ROUTES = [
  "/",
  "/okh",
  "/okh/okh-0001",
  "/facilities",
  "/facilities/okw-1",
  "/match",
  "/solutions",
  "/visualization/sol-1",
];

for (const route of ROUTES) {
  test(`no serious a11y violations: ${route}`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "real-api", "uses fixture ids");
    await page.goto(route);
    await expectNoA11yViolations(page);
  });
}

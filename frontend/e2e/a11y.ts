import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/**
 * Run an axe accessibility scan on the current page and assert there are no
 * serious or critical violations. Feature slices call this on each journey.
 */
export async function expectNoA11yViolations(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  const seriousOrCritical = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  expect(
    seriousOrCritical,
    `a11y violations:\n${seriousOrCritical.map((v) => `- ${v.id}: ${v.help}`).join("\n")}`,
  ).toEqual([]);
}

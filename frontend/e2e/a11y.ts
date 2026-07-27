import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/**
 * Run an axe accessibility scan on the current page and assert there are no
 * serious or critical violations. Feature slices call this on each journey.
 */
export async function expectNoA11yViolations(page: Page): Promise<void> {
  // Wait for animations to finish before scanning.
  //
  // Elements fade in (tw-animate-css), and axe computes contrast from whatever
  // is on screen at that instant. Mid-fade, a colour is blended toward its
  // background, so the scan sees greys that exist in no stylesheet — observed
  // as "#4f4f4f on #a9a9a9", with different values each run. That produced
  // intermittent failures (2-3 in every 5-8 runs) attributable to no component.
  //
  // Waiting for settled animations makes the scan deterministic. It is bounded
  // so an infinite/looping animation cannot hang the suite.
  await page
    .waitForFunction(
      () =>
        document
          .getAnimations()
          .every((a) => a.playState === "finished" || a.playState === "idle"),
      undefined,
      { timeout: 5_000 },
    )
    .catch(() => {
      /* a persistent animation is not itself a failure; scan anyway */
    });

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

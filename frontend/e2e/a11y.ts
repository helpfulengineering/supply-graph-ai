import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/**
 * Run an axe accessibility scan on the current page and assert there are no
 * serious or critical violations. Feature slices call this on each journey.
 */
export async function expectNoA11yViolations(page: Page): Promise<void> {
  // Wait for the document to finish loading before scanning.
  //
  // axe judges the document it is handed, and a document still being parsed is
  // not the one under test. `<title>` is the tell: it lives in <head>, so a
  // scan landing mid-parse reports `document-title` ("Documents must have
  // <title> element") against a page whose title arrives microseconds later.
  //
  // The window is narrow enough to be invisible on an idle machine and real on
  // a loaded one. It widens when a client-side navigation falls back to a full
  // browser navigation — Next does that when an RSC payload fetch fails, which
  // a busy runner makes likely — because that replaces the settled document
  // with a fresh one mid-test. Reproduced under deliberate CPU contention:
  // `document-title`, serious, on a recipe detail page reached by a click.
  //
  // `complete` rather than `domcontentloaded`: a document that has parsed its
  // head but not finished loading can still swap under the scan. If the
  // document IS complete and the title is still missing, that is a real
  // violation and this wait does not hide it.
  await page
    .waitForFunction(() => document.readyState === "complete", undefined, {
      timeout: 5_000,
    })
    .catch(() => {
      /* a page that never reports complete is the scan's problem, not ours */
    });

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

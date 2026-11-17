import path from "node:path";
import { type Page, type TestInfo } from "@playwright/test";

/**
 * A named screenshot taken where the runbook says to look.
 *
 * These are evidence for a person to review, not baselines: nothing compares
 * them to an earlier image, so a changed pixel never fails a run. They are
 * written to `artifacts/uat-evidence/`, which the workflow uploads, and also
 * attached to the test so the HTML report shows them in place.
 *
 * The one-time secret panel (a freshly minted token, a recovery code) is masked.
 * The node is thrown away after the run, but the image is kept for three, and a
 * credential in a screenshot is a habit worth not starting.
 */
const ONE_TIME_SECRET = '[role="group"] pre';

export async function shot(
  page: Page,
  testInfo: TestInfo,
  name: string,
): Promise<void> {
  const file = path.resolve(
    process.cwd(),
    "artifacts/uat-evidence",
    `${name}.png`,
  );
  await page.screenshot({
    path: file,
    fullPage: true,
    mask: [page.locator(ONE_TIME_SECRET)],
  });
  await testInfo.attach(name, { path: file, contentType: "image/png" });
}

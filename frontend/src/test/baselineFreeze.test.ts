import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Baseline freeze guard (Slice 0 of the frontend revamp integration — see
 * notes/frontend-revamp-integration-plan.md).
 *
 * The incoming fork modified EVERY pre-existing Playwright spec (-122 lines
 * across 14 files), including removed assertions and at least one deleted
 * test. Some of that is honest re-expression after a chrome redesign; some is
 * coverage quietly going away. The difference is invisible in a diff that also
 * touches 399 source files.
 *
 * So the black-box suite is frozen by content hash. It is not immutable — it
 * is *load-bearing*: changing one is a deliberate behaviour change that has to
 * be stated, not a detail that rides along inside a large refactor.
 *
 * To change a baseline spec:
 *   1. Make the change in its own commit, with the reason in the message.
 *   2. Re-bless:  BLESS_BASELINE=1 npm run test:unit
 *   3. Commit the manifest change alongside it, so review sees both.
 *
 * `a11y.ts` is frozen too: it holds the shared assertion every spec's
 * accessibility check routes through, so weakening it would silently downgrade
 * the whole suite while every spec still reads as passing.
 */

const MANIFEST = resolve(process.cwd(), "e2e/baseline.manifest.json");

/**
 * The pre-existing suite (as of merge-base c3572e3) plus the Slice 0
 * characterization specs. `mock-api.ts` is deliberately absent: route patterns
 * and fixture wiring must be free to change as endpoints are added.
 */
const BASELINE_FILES = [
  "e2e/a11y.ts",
  "e2e/a11y-journeys.spec.ts",
  "e2e/cooking-domain.spec.ts",
  "e2e/create.spec.ts",
  "e2e/dashboard.spec.ts",
  "e2e/generate.spec.ts",
  "e2e/match.spec.ts",
  "e2e/near-miss-tolerance.spec.ts",
  "e2e/network.spec.ts",
  "e2e/okh-catalog.spec.ts",
  "e2e/okh-detail.spec.ts",
  "e2e/okw-detail.spec.ts",
  "e2e/packages.spec.ts",
  "e2e/screenshots.spec.ts",
  "e2e/settings.spec.ts",
  "e2e/smoke.spec.ts",
  "e2e/visualization.spec.ts",
];

function hash(relPath: string): string {
  const body = readFileSync(resolve(process.cwd(), relPath), "utf-8");
  return createHash("sha256").update(body).digest("hex");
}

function currentHashes(): Record<string, string> {
  return Object.fromEntries(BASELINE_FILES.map((f) => [f, hash(f)]));
}

describe("e2e baseline freeze", () => {
  if (process.env.BLESS_BASELINE) {
    it("re-blesses the manifest", () => {
      writeFileSync(MANIFEST, `${JSON.stringify(currentHashes(), null, 2)}\n`);
      expect(true).toBe(true);
    });
    return;
  }

  const recorded = JSON.parse(readFileSync(MANIFEST, "utf-8")) as Record<string, string>;
  const actual = currentHashes();

  it("covers exactly the files the manifest records", () => {
    // A spec dropped from BASELINE_FILES would otherwise stop being checked
    // without anything failing — the same silent-loss shape this guards.
    expect(Object.keys(actual).sort()).toEqual(Object.keys(recorded).sort());
  });

  it.each(BASELINE_FILES)("%s is unchanged since it was blessed", (file) => {
    expect(
      actual[file],
      `${file} changed.\n\n` +
        "Baseline specs are the contract the frontend revamp integration is " +
        "verified against. If this edit is a deliberate behaviour change, put " +
        "it in its own commit with the reason, re-bless with " +
        "`BLESS_BASELINE=1 npm run test:unit`, and commit the manifest " +
        "alongside it.",
    ).toBe(recorded[file]);
  });
});

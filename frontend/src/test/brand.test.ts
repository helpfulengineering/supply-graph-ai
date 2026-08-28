import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { renderMarkSvg } from "../components/layout/mark";
import {
  BRAND_GROUND_DARK,
  BRAND_GROUND_LIGHT,
  BRAND_INK_DARK,
  BRAND_INK_LIGHT,
  BRAND_INK_MUTED_DARK,
  BRAND_INK_MUTED_LIGHT,
  BRAND_NAME,
  BRAND_RAMP_DARK,
  BRAND_TITLE,
} from "../../app/brand";

/**
 * Brand-coherence guards.
 *
 * The favicon used to be a hand-maintained copy of the logo's path data, kept
 * in step by a comment asking the next editor to remember. It did not stay in
 * step, and a tab that shows a different mark — or a different product name —
 * than the app behind it is how an interface starts feeling like two products
 * stapled together.
 *
 * So the three couplings that keep the mark attached are asserted here rather
 * than trusted: the checked-in favicon IS the generator's output, the colours
 * it bakes ARE the Warm world's tokens, and the name in the document head IS
 * the name the mark answers to.
 */

const FRONTEND = join(import.meta.dirname, "..", "..");
const TOKENS = readFileSync(
  join(FRONTEND, "src", "styles", "tokens.css"),
  "utf8",
);

/**
 * Read a custom property out of the Warm world, in the requested polarity.
 *
 * Warm is the world with no `data-ttm-theme` attribute, so its two blocks are
 * the bare `:root` and `:root.dark` selectors at the top of the file — which
 * is exactly why it is the world the head mirrors: it is what a visitor who
 * has chosen nothing actually sees.
 */
function warmToken(name: string, mode: "light" | "dark"): string {
  const start = TOKENS.indexOf(
    mode === "dark"
      ? ':root.dark,\n:root[data-ttm-theme="ttm"].dark {'
      : ':root,\n:root[data-ttm-theme="ttm"] {',
  );
  expect(start, `Warm ${mode} block not found in tokens.css`).toBeGreaterThan(
    -1,
  );
  const block = TOKENS.slice(start, TOKENS.indexOf("\n}", start));
  const match = block.match(new RegExp(`--${name}:\\s*([^;]+);`));
  expect(match, `--${name} not found in the Warm ${mode} block`).not.toBeNull();
  return match![1].trim();
}

describe("the favicon is the app's mark", () => {
  it("app/icon.svg is exactly what the generator emits", () => {
    const onDisk = readFileSync(join(FRONTEND, "app", "icon.svg"), "utf8");
    const generated = renderMarkSvg({
      ramp: BRAND_RAMP_DARK,
      ground: BRAND_GROUND_DARK,
      label: BRAND_NAME,
    });

    expect(
      onDisk,
      "app/icon.svg has drifted from src/components/layout/mark.ts — run `npm run gen:brand`",
    ).toBe(generated);
  });
});

describe("baked brand colour tracks the token layer", () => {
  it("the favicon ramp is the Warm dark iridescent ramp", () => {
    const fromTokens = ["a", "b", "c", "d", "e"].map((k) =>
      warmToken(`ttm-irid-${k}`, "dark"),
    );
    expect(
      [...BRAND_RAMP_DARK],
      "BRAND_RAMP_DARK in app/brand.ts no longer matches --ttm-irid-* for the Warm dark world",
    ).toEqual(fromTokens);
  });

  it("the theme-color grounds are the Warm backgrounds", () => {
    expect(BRAND_GROUND_DARK).toBe(warmToken("ttm-bg", "dark"));
    expect(BRAND_GROUND_LIGHT).toBe(warmToken("ttm-bg", "light"));
  });

  it("the share card's ink is the Warm dark text ramp", () => {
    expect(BRAND_INK_DARK).toBe(warmToken("ttm-text", "dark"));
    expect(BRAND_INK_MUTED_DARK).toBe(warmToken("ttm-text-muted", "dark"));
  });

  it("the global error boundary's light ink is the Warm light text ramp", () => {
    expect(BRAND_INK_LIGHT).toBe(warmToken("ttm-text", "light"));
    expect(BRAND_INK_MUTED_LIGHT).toBe(warmToken("ttm-text-muted", "light"));
  });
});

describe("the product has one name", () => {
  it("the document title states the name the mark answers to", () => {
    // The mark's accessible name is what a screen reader calls the logo, and
    // the head is what a tab, a bookmark, and a share card call the app. They
    // said different things — "Manager" in the mark, "Matchmaker" in the head.
    expect(BRAND_TITLE).toContain(BRAND_NAME);

    const logo = readFileSync(
      join(FRONTEND, "src", "components", "layout", "Logo.tsx"),
      "utf8",
    );
    expect(logo).toContain(`aria-label="${BRAND_NAME}"`);

    const readme = readFileSync(join(FRONTEND, "..", "README.md"), "utf8");
    expect(readme.split("\n")[0]).toContain(BRAND_NAME);
  });
});

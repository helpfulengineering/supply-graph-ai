import { expect } from "@playwright/test";
import { test } from "./mock-api";
import { expectNoA11yViolations } from "./a11y";
import { THEMES } from "../src/hooks/useDarkMode";

/**
 * The contrast gate: every world x every polarity must pass WCAG AA before it
 * can ship. This is Phase 3 of the overhaul, landed deliberately BEFORE the
 * chrome repaint — the gate has to exist while the risky changes are written,
 * because reversing that order is how design systems ship inaccessible
 * palettes.
 *
 * Adding a world to THEMES extends this matrix automatically; there is no
 * second list to update. Contrast is computed by axe from runtime-resolved
 * token values on the live page, never from numbers copied into a test — so a
 * palette edit in tokens.css is judged by what it actually renders.
 *
 * The scan runs on the dashboard: the widest surface (map chrome, stat cards,
 * status badges, banners, buttons) and every token family in one viewport.
 * Feature-specific journeys keep their own scans in a11y-journeys.spec.ts; a
 * full route sweep per variant would cost minutes for surfaces those journeys
 * already cover in the default world.
 */

for (const { slug, label } of THEMES) {
  for (const mode of ["light", "dark"] as const) {
    test(`no serious a11y violations: ${label} ${mode}`, async ({ page }) => {
      // Seed the stored preference before any script runs, so the pre-paint
      // script in app/theme-script.tsx applies the variant exactly the way it
      // does for a returning visitor — the mechanism under test, not a
      // hand-stamped attribute.
      await page.addInitScript(
        ([themeSlug, themeMode]) => {
          localStorage.setItem("ohm-theme", themeSlug);
          localStorage.setItem("ohm-color-scheme", themeMode);
        },
        [slug, mode],
      );

      await page.goto("/");
      await expectNoA11yViolations(page);
    });
  }
}

/**
 * The theme picker's swatches must be the worlds they claim to preview.
 *
 * `useThemeSwatches` reads each world's accent by briefly applying it to
 * <html> — chosen over a per-world colour map in CSS precisely so there is no
 * second copy of ten colours free to drift. That argument only holds if the
 * resolution is correct, and jsdom cannot check it: it does not implement the
 * cascade, so the unit tests can only assert the mechanism. This is where the
 * values are judged, against the real one.
 *
 * Adding a world to THEMES extends this automatically, like the matrix above.
 */
test("theme picker swatches match each world's own accent", async ({
  page,
}) => {
  await page.goto("/");
  // Captured BEFORE the drawer mounts, and deliberately not asserted as null:
  // the pre-paint script in app/theme-script.tsx stamps the resolved world
  // onto <html>, so a default instance already reads data-ttm-theme="ttm"
  // here. The property is that the picker leaves the attribute as it found it,
  // whatever that was — pinning a value would test the theme script instead.
  const before = await page.evaluate(() =>
    document.documentElement.getAttribute("data-ttm-theme"),
  );
  await page.getByRole("button", { name: "Site menu" }).click();

  // The truth: each world's accent as the live cascade resolves it, read the
  // long way round — one page state per world, no shared machinery with the
  // hook under test.
  const expected: Record<string, string> = {};
  for (const { slug } of THEMES) {
    expected[slug] = await page.evaluate((s) => {
      const root = document.documentElement;
      const before = root.getAttribute("data-ttm-theme");
      root.setAttribute("data-ttm-theme", s);
      const value = getComputedStyle(root)
        .getPropertyValue("--ttm-accent-cta")
        .trim();
      if (before === null) root.removeAttribute("data-ttm-theme");
      else root.setAttribute("data-ttm-theme", before);
      return value;
    }, slug);
  }

  const rendered = await page.evaluate(() =>
    Array.from(
      document.querySelectorAll<HTMLInputElement>(
        'input[name="ohm-theme-pick"]',
      ),
    ).map((input) => {
      const chip = input.parentElement?.querySelector("span[aria-hidden]");
      return {
        slug: input.value,
        // Computed, so a swatch that failed to resolve shows up as a
        // transparent or inherited colour rather than silently passing.
        background: chip ? getComputedStyle(chip).backgroundColor : "",
      };
    }),
  );

  expect(rendered).toHaveLength(THEMES.length);
  for (const { slug, background } of rendered) {
    expect(background, `${slug} swatch is unpainted`).not.toBe(
      "rgba(0, 0, 0, 0)",
    );
    // Both sides are computed values from the same engine, so they are
    // directly comparable without parsing colour syntax.
    const want = await page.evaluate((c) => {
      const el = document.createElement("span");
      el.style.backgroundColor = c;
      document.body.appendChild(el);
      const v = getComputedStyle(el).backgroundColor;
      el.remove();
      return v;
    }, expected[slug]);
    expect(background, `${slug} swatch does not match its world`).toBe(want);
  }

  // The picker must leave the document in the world it found it in — the
  // resolver flips <html> ten times to read the palettes, and a missed restore
  // would silently strand every visitor in whichever world the loop ended on.
  expect(
    await page.evaluate(() =>
      document.documentElement.getAttribute("data-ttm-theme"),
    ),
  ).toBe(before);
});

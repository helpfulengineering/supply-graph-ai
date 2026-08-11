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

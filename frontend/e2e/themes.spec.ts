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
test("each theme name is painted in its own world's accent", async ({
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

  // The picker paints a beat after it opens, and waiting for it is the point:
  // the resolver deliberately stands aside for the drawer's entrance rather
  // than resolving on the frame the menu appears, which is what used to stall
  // the open. Reading straight after the click was a race this spec happened
  // to win.
  await expect
    .poll(
      async () =>
        page.evaluate(
          () =>
            new Set(
              Array.from(
                document.querySelectorAll<HTMLInputElement>(
                  'input[name="ohm-theme-pick"]',
                ),
              ).map((input) => {
                const name =
                  input.parentElement?.querySelector("span.truncate");
                return name ? getComputedStyle(name).color : "";
              }),
            ).size,
        ),
      { message: "the picker never painted its worlds" },
    )
    .toBe(THEMES.length);

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

  // The name itself carries the world now — one marker per row rather than a
  // radio and a swatch dot. The colour is the accent blended toward the
  // foreground (see ThemeSwatch.ink), so it cannot be compared to the raw
  // accent; what must hold is that every world paints its name, and that no
  // two worlds paint it the same.
  const rendered = await page.evaluate(() =>
    Array.from(
      document.querySelectorAll<HTMLInputElement>(
        'input[name="ohm-theme-pick"]',
      ),
    ).map((input) => {
      const name = input.parentElement?.querySelector("span.truncate");
      return {
        slug: input.value,
        // Computed, so a name that failed to resolve shows up as the inherited
        // foreground rather than silently passing.
        colour: name ? getComputedStyle(name).color : "",
        font: name ? getComputedStyle(name).fontFamily : "",
      };
    }),
  );

  expect(rendered).toHaveLength(THEMES.length);
  const foreground = await page.evaluate(() =>
    getComputedStyle(document.documentElement)
      .getPropertyValue("--ttm-text")
      .trim(),
  );
  for (const { slug, colour } of rendered) {
    expect(colour, `${slug} name is unpainted`).not.toBe("");
    expect(colour, `${slug} name is the plain foreground`).not.toBe(foreground);
  }
  const distinct = new Set(rendered.map((r) => r.colour));
  expect(
    distinct.size,
    `worlds share a name colour: ${rendered.map((r) => `${r.slug}=${r.colour}`).join(", ")}`,
  ).toBe(THEMES.length);

  // Terminal and Mono repoint every font stack at the monospace face, so their
  // names should not render in the same family as the others.
  const mono = rendered.filter(
    (r) => r.slug === "terminal" || r.slug === "mono",
  );
  const warm = rendered.find((r) => r.slug === "ttm");
  for (const m of mono) {
    expect(m.font, `${m.slug} does not preview its own typeface`).not.toBe(
      warm?.font,
    );
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

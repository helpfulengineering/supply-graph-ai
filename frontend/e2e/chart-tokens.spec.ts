import { test, expect } from "./mock-api";
import { THEMES } from "../src/hooks/useDarkMode";

/**
 * A categorical ramp is only useful if its stops are distinguishable, and that
 * is not something the palette guarantees for free: most worlds deliberately
 * point --ttm-control and --ttm-accent-cta at the same colour (right for
 * chrome, fatal for series). Pointing --chart-* at those role tokens collided
 * in 12 of 20 variants — two series, one colour, silently.
 *
 * So this asserts the property the ramp actually needs, across every variant,
 * from runtime-resolved values rather than numbers copied into a test.
 */

test("chart ramp resolves to five distinct colours in every variant", async ({
  page,
}) => {
  await page.goto("/");

  const collisions: string[] = [];
  for (const { slug, label } of THEMES) {
    for (const mode of ["light", "dark"] as const) {
      const stops = await page.evaluate(
        ([themeSlug, themeMode]) => {
          const root = document.documentElement;
          root.setAttribute("data-ttm-theme", themeSlug);
          root.classList.toggle("dark", themeMode === "dark");
          const style = getComputedStyle(root);
          return [1, 2, 3, 4, 5].map((i) =>
            style.getPropertyValue(`--chart-${i}`).trim().toLowerCase(),
          );
        },
        [slug, mode],
      );

      expect(
        stops.every((s) => s.length > 0),
        `${label} ${mode}: unresolved stop`,
      ).toBe(true);
      if (new Set(stops).size !== stops.length) {
        collisions.push(`${label} ${mode}: ${stops.join(" ")}`);
      }
    }
  }

  expect(
    collisions,
    `chart ramp collisions:\n${collisions.join("\n")}`,
  ).toEqual([]);
});

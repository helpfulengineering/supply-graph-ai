import { test, expect } from "./mock-api";
import { THEMES } from "../src/hooks/useDarkMode";

/**
 * The process swatches ride the chart ramp, which e2e/chart-tokens.spec.ts
 * already holds distinct. What that spec cannot see is the sixth swatch: the
 * neutral `other` is a different token in a different file, and a world whose
 * muted text happens to land on one of its own hues would give two families
 * one colour with nothing to catch it.
 */

const SWATCHES = [
  "--process-additive",
  "--process-subtractive",
  "--process-forming",
  "--process-joining",
  "--process-finishing",
  "--process-other",
];

test("process swatches resolve to six distinct colours in every variant", async ({
  page,
}) => {
  await page.goto("/");
  // The dev server injects the stylesheet after load, and a variable read
  // before it lands is empty for the same reason a missing one is.
  await page.waitForFunction(
    () =>
      getComputedStyle(document.documentElement)
        .getPropertyValue("--process-additive")
        .trim().length > 0,
  );

  const collisions: string[] = [];
  for (const { slug, label } of THEMES) {
    for (const mode of ["light", "dark"] as const) {
      const stops = await page.evaluate(
        ([themeSlug, themeMode, tokens]) => {
          const root = document.documentElement;
          root.setAttribute("data-ttm-theme", themeSlug as string);
          root.classList.toggle("dark", themeMode === "dark");
          const style = getComputedStyle(root);
          return (tokens as string[]).map((t) =>
            style.getPropertyValue(t).trim().toLowerCase(),
          );
        },
        [slug, mode, SWATCHES] as const,
      );

      expect(
        stops.every((s) => s.length > 0),
        `${label} ${mode}: unresolved swatch`,
      ).toBe(true);
      if (new Set(stops).size !== stops.length) {
        collisions.push(`${label} ${mode}: ${stops.join(" ")}`);
      }
    }
  }

  expect(
    collisions,
    `process swatch collisions:\n${collisions.join("\n")}`,
  ).toEqual([]);
});

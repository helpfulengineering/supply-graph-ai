import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { test } from "./mock-api";

/**
 * The four images the README embeds, regenerated.
 *
 * They were captured by hand, which is why they went stale: the dashboard shot
 * still showed Mission Control in the sitemap after it was renamed to Operator
 * Tools, and all four predate the map reading the world's own colour. A README
 * is the first thing anyone sees of this project and it was advertising an
 * interface that no longer exists.
 *
 * Run on demand rather than in the gate — `npx playwright test --project=mocked
 * e2e/readme-assets.spec.ts` — because these are committed artefacts, not
 * assertions, and a lane that rewrites four binaries on every CI run would put
 * a diff in every pull request that touched the frontend.
 *
 * The mocked lane supplies the data, so the catalogue and the map are the same
 * fixture world the rest of the suite runs against: repeatable, and free of
 * anything real. `?theme=&mode=` is the app's own shareable-look parameter, so
 * the world is pinned the way a reader would pin it rather than by reaching
 * into storage.
 */

const OUT = join(import.meta.dirname, "..", "..", "docs", "assets", "ux");

interface Shot {
  file: string;
  path: string;
  theme: string;
  mode: "light" | "dark";
  /** Open the sitemap before capturing. */
  drawer?: boolean;
  /** Crop to the top of the page instead of capturing its full height. */
  fold?: boolean;
}

const SHOTS: Shot[] = [
  {
    file: "dashboard-warm-light",
    path: "/",
    theme: "ttm",
    mode: "light",
    fold: true,
  },
  {
    file: "dashboard-synthwave-dark",
    path: "/",
    theme: "synthwave",
    mode: "dark",
    fold: true,
  },
  {
    file: "catalog-blueprint-dark",
    path: "/okh",
    theme: "blueprint",
    mode: "dark",
    fold: true,
  },
  {
    file: "sitemap-drawer",
    path: "/",
    theme: "ttm",
    mode: "light",
    drawer: true,
  },
];

test.describe("README assets", () => {
  // Wide enough that the two-column panels are in their desktop layout, which
  // is what the README's side-by-side table is showing.
  test.use({ viewport: { width: 1280, height: 900 } });

  for (const shot of SHOTS) {
    test(`capture ${shot.file}`, async ({ page }) => {
      mkdirSync(OUT, { recursive: true });
      await page.goto(`${shot.path}?theme=${shot.theme}&mode=${shot.mode}`);
      await page.waitForLoadState("networkidle");

      if (shot.drawer) {
        await page.getByRole("button", { name: "Site menu" }).click();
        // The drawer slides in; capturing mid-animation gives a blurred panel
        // half off the right edge.
        await page.waitForTimeout(400);
      }

      // Leaflet loads its tiles lazily and the charts animate their bars up
      // from zero. Both finish well inside this, and a screenshot taken before
      // they do is the one thing a reader would notice.
      await page.waitForTimeout(1200);

      await page.screenshot({
        path: join(OUT, `${shot.file}.png`),
        fullPage: !shot.fold,
      });
    });
  }
});

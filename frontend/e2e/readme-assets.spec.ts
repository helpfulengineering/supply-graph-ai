import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { test } from "./mock-api";

/**
 * The images the README embeds, regenerated.
 *
 * They were captured by hand, which is why they went stale: the dashboard shot
 * still showed Mission Control in the sitemap after it was renamed to Operator
 * Tools, and all four predate the map reading the world's own colour. A README
 * is the first thing anyone sees of this project and it was advertising an
 * interface that no longer exists.
 *
 * The set now covers what the README claims about the interface rather than
 * only what it looks like: the theme picker, the keyboard contract, the
 * accessibility table, the skip link, and the 360px layout. Each of those is a
 * gate somewhere in the suite, and a claim with no picture of it reads as
 * marketing.
 *
 * Run on demand, in its own lane:
 *
 *     npx playwright test --project=assets
 *
 * It captures rather than asserts, and what it writes is committed binaries —
 * which is why it is a project of its own and not part of `npm run e2e`. The
 * first version of this file sat in the default lane, so an unrelated frontend
 * change arrived with four rewritten screenshots attached and nothing to say
 * why.
 *
 * The mocked lane supplies the data, so the catalogue and the map are the same
 * fixture world the rest of the suite runs against: repeatable, and free of
 * anything real. `?theme=&mode=` is the app's own shareable-look parameter, so
 * the world is pinned the way a reader would pin it rather than by reaching
 * into storage.
 */

const OUT = join(import.meta.dirname, "..", "..", "docs", "assets", "ux");

/** Wide enough for the two-column panels to be in their desktop layout. */
const DESKTOP = { width: 1280, height: 900 };

/** The floor the responsive lane gates at, so the README shows what it asserts. */
const PHONE = { width: 360, height: 780 };

interface Shot {
  file: string;
  path: string;
  theme: string;
  mode: "light" | "dark";
  /** Open the sitemap before capturing. */
  drawer?: boolean;
  /** Scroll the open drawer to its foot, where Theme and Keyboard sit. */
  drawerFoot?: boolean;
  /** Reveal the skip link by tabbing into the page from the address bar. */
  skipLink?: boolean;
  /** Crop to the top of the page instead of capturing its full height. */
  fold?: boolean;
  /** Defaults to DESKTOP. */
  viewport?: { width: number; height: number };
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
  // fold, not fullPage. The drawer is a viewport-height panel that scrolls
  // inside itself, so a full-page capture of a tall dashboard rendered it as a
  // column ending in mid-air with the Theme and Keyboard blocks cut off — the
  // README was illustrating the sitemap with a picture of it truncated.
  {
    file: "sitemap-drawer",
    path: "/",
    theme: "ttm",
    mode: "light",
    drawer: true,
    fold: true,
  },
  {
    file: "theme-picker",
    path: "/",
    theme: "ttm",
    mode: "light",
    drawer: true,
    drawerFoot: true,
    fold: true,
  },
  // One shot, not one per section. /help ends just below the accessibility
  // table, so anchoring on #h-keys and on #h-a11y both hit the page's maximum
  // scroll and produced two byte-identical images. The frame they share holds
  // both tables anyway, which is the thing worth showing: the keyboard
  // contract and the accessibility contract, side by side and generated from
  // the same constants the chrome uses.
  {
    file: "help-keyboard-accessibility",
    path: "/help#h-keys",
    theme: "terminal",
    mode: "dark",
    fold: true,
  },
  {
    file: "skip-link",
    path: "/",
    theme: "ttm",
    mode: "light",
    skipLink: true,
    fold: true,
  },
  {
    file: "dashboard-mobile",
    path: "/",
    theme: "ocean",
    mode: "light",
    fold: true,
    viewport: PHONE,
  },
];

test.describe("README assets", () => {
  test.use({ viewport: DESKTOP });

  for (const shot of SHOTS) {
    test(`capture ${shot.file}`, async ({ page }) => {
      mkdirSync(OUT, { recursive: true });
      if (shot.viewport) await page.setViewportSize(shot.viewport);

      // `?theme=&mode=` goes before any #fragment, so a shot can pin the world
      // and land on a section heading at the same time.
      const [path, hash] = shot.path.split("#");
      const query = `?theme=${shot.theme}&mode=${shot.mode}`;
      await page.goto(`${path}${query}${hash ? `#${hash}` : ""}`);
      await page.waitForLoadState("networkidle");

      // `next dev` mounts its own floating dev-tools button into a
      // <nextjs-portal>. It sat in the bottom-left corner of every committed
      // screenshot, and — being focusable — it also answered the first Tab,
      // which is the keystroke the skip-link shot exists to photograph.
      await page.addStyleTag({
        content: "nextjs-portal { display: none !important; }",
      });

      if (shot.drawer) {
        await page.getByRole("button", { name: "Site menu" }).click();
        // The drawer slides in; capturing mid-animation gives a blurred panel
        // half off the right edge.
        await page.waitForTimeout(400);
      }

      if (shot.drawerFoot) {
        await page
          .getByRole("dialog", { name: "Site menu" })
          .evaluate((el) => el.scrollTo({ top: el.scrollHeight }));
        await page.waitForTimeout(200);
      }

      // Leaflet loads its tiles lazily and the charts animate their bars up
      // from zero. Both finish well inside this, and a screenshot taken before
      // they do is the one thing a reader would notice.
      await page.waitForTimeout(1200);

      // After the settle, not before it. The fragment is resolved once at
      // navigation, when the section it names has not hydrated yet, and the
      // panels that mount above it then push the heading back off screen — the
      // first run of this captured the top of /help for both anchored shots.
      //
      // scrollIntoView, not Playwright's scrollIntoViewIfNeeded: the heading
      // had been pushed to the last few pixels of the viewport, which counts
      // as "in view", so the if-needed form did nothing and the shot was the
      // top of the page a second time. This one puts the section at the top
      // unconditionally, and honours the `scroll-mt` that keeps the sticky
      // header off the target.
      if (hash) {
        await page
          .locator(`#${hash}`)
          .evaluate((el) => el.scrollIntoView({ block: "start" }));
        await page.waitForTimeout(300);
      }

      if (shot.skipLink) {
        // One Tab from a fresh load. The skip link is the first focusable
        // thing in the document precisely so this is all it takes, and the
        // shot is worth having because the control is invisible until it has
        // focus — there is no other way to show that it exists.
        await page.keyboard.press("Tab");
      }

      await page.screenshot({
        path: join(OUT, `${shot.file}.png`),
        fullPage: !shot.fold,
      });
    });
  }
});

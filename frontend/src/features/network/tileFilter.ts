import { parseRgb } from "../../lib/contrastInk";

/**
 * The map's ground, in the world's own colour.
 *
 * Markers, clusters and the key already re-theme — they read `--chart-1` and
 * `--chart-2` through `sourceColor`. The tiles did not, and they are most of
 * the pixels: OpenStreetMap's raster tiles arrive from a server already
 * painted, so the token layer cannot reach them the way it reaches everything
 * else on the page.
 *
 * The previous treatment was one fixed rule — `invert(1) hue-rotate(180deg)`
 * on `.dark` — which does turn light tiles dark, but lands on whatever hue
 * inverting OSM's blue water happens to produce. That hue is the same in all
 * twenty worlds, so Warm, Ocean and Synthwave all got the identical teal map,
 * and every light world got no treatment at all: raw OSM beige-and-green
 * inside a themed page. The map was the one surface that did not answer to
 * the theme.
 *
 * So the filter is computed from a token instead of written down. `grayscale`
 * strips OSM's palette, `sepia` re-tints it to a known hue, and `hue-rotate`
 * carries that hue to the world's — which makes the map a monochrome drawing
 * in the world's colour, land and water still separated by lightness. Anything
 * new added to tokens.css is themed by construction, with nothing to remember.
 */

/** Sepia's resulting hue in degrees — the origin every rotation starts from. */
const SEPIA_HUE = 38;

/**
 * A token's value as channels, whichever way it was written.
 *
 * `lib/contrastInk`'s `parseRgb` reads the `rgb(r, g, b)` that
 * `getComputedStyle` returns for a resolved *property* — but a custom property
 * is not resolved, it is handed back as the literal text of the declaration,
 * and tokens.css writes colour as hex. So `--ttm-accent-cta` arrives as
 * "#38bdf8", `parseRgb` finds two numbers in it, and the whole map fell back
 * to grey — the exact bug this file exists to fix, reintroduced one layer
 * down and silently, because "no hue" is a legitimate answer for a neutral
 * world and looks identical to a failed parse.
 */
function toRgb(color: string): { r: number; g: number; b: number } | null {
  const hex = color.trim().match(/^#([\da-f]{3}|[\da-f]{6})$/i)?.[1];
  if (hex) {
    const full =
      hex.length === 3
        ? hex
            .split("")
            .map((c) => c + c)
            .join("")
        : hex;
    return {
      r: parseInt(full.slice(0, 2), 16),
      g: parseInt(full.slice(2, 4), 16),
      b: parseInt(full.slice(4, 6), 16),
    };
  }
  return parseRgb(color);
}

/**
 * Hue of a resolved colour, in degrees, or null if it has none.
 *
 * `null` for a grey: a world whose ground is neutral (Mono, Terminal) has no
 * hue to carry, and rotating toward an arbitrary one would invent a colour the
 * theme did not choose. The caller renders those unsaturated, which is what
 * those worlds are.
 */
export function hueOf(color: string): number | null {
  const rgb = toRgb(color);
  if (!rgb) return null;
  const { r, g, b } = rgb;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  // Under about 2% of the range the "hue" is parse noise on a grey.
  if (delta < 255 * 0.02) return null;

  let hue: number;
  if (max === r) hue = ((g - b) / delta) % 6;
  else if (max === g) hue = (b - r) / delta + 2;
  else hue = (r - g) / delta + 4;

  hue *= 60;
  return hue < 0 ? hue + 360 : hue;
}

export interface TileFilterOptions {
  /**
   * The world's accent, resolved — `--ttm-accent-cta`. Supplies the hue.
   *
   * Not `--ttm-bg`, which was the first choice and the wrong one: most worlds
   * ground on a near-neutral (that is what makes them readable), so the hue
   * came back null and every dark world drew the same grey map — the original
   * defect with a different colour. The accent is the token that actually
   * differs between worlds, and it is what a reader would name if asked what
   * colour the app is.
   */
  accent: string;
  /** Dark polarity, which needs the tiles inverted before they are tinted. */
  isDark: boolean;
}

/**
 * The CSS `filter` for the tile pane in the current world.
 *
 * Pure and string-returning so the mapping can be asserted per world without a
 * map, a network, or a browser — see tileFilter.test.ts.
 */
export function tileFilter({ accent, isDark }: TileFilterOptions): string {
  const hue = hueOf(accent);

  // Order matters. Invert first, while the tiles still carry their own
  // luminance, then flatten, then tint: inverting after the tint would undo
  // the hue the world just supplied.
  const steps: string[] = [];
  if (isDark) steps.push("invert(1)", "brightness(0.92)");
  steps.push("grayscale(1)");

  if (hue === null) {
    // A neutral world stays neutral — the greyscale IS the answer.
    steps.push("contrast(0.9)");
    return steps.join(" ");
  }

  steps.push(
    "sepia(1)",
    `hue-rotate(${Math.round(hue - SEPIA_HUE)}deg)`,
    // Restrained on purpose: the map is the ground a reader looks past, and
    // the two source colours have to stay the loudest things on it. Enough
    // hue to belong to the world, not enough to compete with the key — the
    // markers read chart-1 and chart-2, which are near neighbours of this
    // hue, so a saturated map would camouflage the points on it.
    "saturate(0.55)",
    "contrast(0.9)",
  );
  return steps.join(" ");
}

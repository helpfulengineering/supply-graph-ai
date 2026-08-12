/**
 * Brand constants for the document head.
 *
 * Everything a browser, crawler, or home screen learns about this app before a
 * single stylesheet loads: the name, the one-line description, the tab colour,
 * and the ramp the favicon bakes in.
 *
 * These are the one legitimate exception to "colour lives only in tokens.css".
 * A <meta name="theme-color"> and a standalone .svg are read before and outside
 * the cascade, so neither can resolve a `var()`. They are still not a second
 * source of truth: src/test/brand.test.ts parses tokens.css and fails if any
 * value here has drifted from the Warm world it mirrors. Change the token,
 * run the test, follow the failure.
 *
 * Warm is the right world to mirror because it is what a visitor with no
 * `data-ttm-theme` attribute gets — the default the tab strip will sit beside.
 */

/**
 * The product name.
 *
 * "Manager", not "Matchmaker". Matching is one of the things OHM does, and the
 * head advertising a different noun than the README, the dashboard heading, and
 * the mark's own accessible name is exactly the kind of drift that leaves a
 * favicon feeling detached from the app behind it.
 */
export const BRAND_NAME = "Open Hardware Manager";
export const BRAND_SHORT = "OHM";
export const BRAND_TITLE = `${BRAND_SHORT} — ${BRAND_NAME}`;

/**
 * The crumb under the dashboard's h1, said once more for share cards.
 *
 * Structured rather than written out, because each term is also the name of a
 * destination and the dashboard links them. The string is derived from the
 * terms and not the other way round, so renaming one cannot leave the share
 * card saying a word the hero no longer uses.
 *
 * `supply chains` points at /match rather than a list of its own: a supply tree
 * is a result, opened from the match that produced it, so there is no
 * collection to browse — the term points at where one is made.
 */
export const BRAND_TAGLINE_LINKS = [
  { label: "designs", href: "/okh" },
  { label: "facilities", href: "/facilities" },
  { label: "supply chains", href: "/match" },
] as const;

export const BRAND_TAGLINE = BRAND_TAGLINE_LINKS.map((t) => t.label).join(
  " · ",
);

export const BRAND_DESCRIPTION =
  "Browse open hardware designs, match them to the manufacturing facilities that can build them, and follow the supply tree that results.";

/** Mirrors :root[data-ttm-theme="ttm"].dark --ttm-irid-a..e in tokens.css. */
export const BRAND_RAMP_DARK = [
  "#ff9a9e",
  "#fecfef",
  "#a1c4fd",
  "#c2e9fb",
  "#d4fc79",
] as const;

/** Mirrors --ttm-bg for the Warm world, dark and light. */
export const BRAND_GROUND_DARK = "#0f0b08";
export const BRAND_GROUND_LIGHT = "#faf7f2";

/** Mirrors --ttm-text and --ttm-text-muted, Warm dark — the share card's ink. */
export const BRAND_INK_DARK = "#f4efe8";
export const BRAND_INK_MUTED_DARK = "#9c9184";

/**
 * The same two, Warm light — for app/global-error.tsx.
 *
 * The share card is a dark image and needs one polarity; the global error
 * boundary is a live document that replaces the whole page, including the
 * element the theme attribute is set on. `prefers-color-scheme` is the only
 * signal it has left, so it needs both grounds and both inks.
 */
export const BRAND_INK_LIGHT = "#241c15";
export const BRAND_INK_MUTED_LIGHT = "#675d51";

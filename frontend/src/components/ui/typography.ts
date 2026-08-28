/**
 * Canonical heading and text roles.
 *
 * The third of the trio with `field.ts` (controls) and `surface.ts` (panels),
 * and the same story: `tokens.css` has carried a type scale since Phase 2 and
 * nothing read it. Every heading picked a Tailwind step by hand, so the app
 * ended up with two sizes for a page title (`text-xl`, `text-2xl`), two for a
 * section title, and — the one that actually shows — a single "section label"
 * role spelled `text-sm` on twenty-two content pages and `text-xs` in the
 * drawer. Nobody decided that.
 *
 * These name the ROLE; the utility they resolve to names the rung on the
 * scale, and the rung's value lives in the token file. A component saying
 * `text-h4` is reaching past this module for a number it should not be
 * choosing — use the role.
 *
 * The rungs were picked so that adopting these changed no pixel: the app's
 * headings already sat at 1.25 / 1.125 / 1 / 0.875rem, and the missing 1.125
 * rung was added to the scale rather than the heading rounded onto a rung that
 * happened to exist. Tokenizing is not a redesign.
 */

/** The page's own `<h1>`. One per route, rendered by PageHero. */
export const PAGE_TITLE = "text-h4 font-semibold tracking-tight text-heading";

/** A titled division of a page — the `<h2>` above a group of panels. */
export const SECTION_TITLE = "text-h5 font-semibold text-heading";

/** The heading inside a card or panel. */
export const CARD_TITLE = "text-body font-semibold text-heading";

/**
 * The small uppercase eyebrow that names a group — "Coverage", "Identity".
 * It is a heading, so it belongs on a heading tag; it just does not look like
 * one.
 */
export const SECTION_LABEL =
  "text-small font-semibold uppercase tracking-wide text-muted-foreground";

/**
 * SECTION_LABEL for dense chrome — the drawer's DATA / THEME / KEYBOARD.
 *
 * A second size for one role needs a reason, and the reason is the same one
 * `field.ts` gives for FIELD_SM: chrome is denser than content by design, and
 * collapsing the two would push the drawer's labels up to content scale in a
 * panel that is deliberately compact. Two sizes, one role, both named.
 */
export const SECTION_LABEL_SM =
  "text-caption font-semibold uppercase tracking-wide text-muted-foreground";

/**
 * The single large figure on a stat card — a KPI, a facility count.
 *
 * A role, not a size, and it had the same two-spellings problem the headings
 * had: `text-3xl font-bold tabular-nums` on the visualization KPIs and
 * `text-2xl font-bold` on the dashboard's, which is a decision nobody made.
 * `tabular-nums` belongs to the role rather than to one of its uses: a column
 * of counts that shifts width as the digits change is the defect the figure
 * exists to avoid.
 */
export const STAT_VALUE =
  "text-h3 font-bold leading-none tabular-nums text-heading";

/** Supporting copy under a heading. */
export const BODY_MUTED = "text-small text-muted-foreground";

/** The smallest supporting text — counts, hints, timestamps. */
export const CAPTION = "text-caption text-muted-foreground";

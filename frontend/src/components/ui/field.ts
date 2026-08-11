/**
 * Canonical form-control classes.
 *
 * There were seventeen hand-styled `<select>`s and sixty-four `<input>`s, in
 * six near-identical spellings that drifted apart over time — different
 * borders, different padding, and inconsistent focus rings, which is an
 * accessibility problem and not just an aesthetic one.
 *
 * These are plain string constants rather than wrapper components on purpose:
 * the elements keep their own props, refs, and event handlers (some are
 * controlled by URL state, some by forms), so a wrapper would have to
 * re-expose all of it for no gain. Tailwind scans these literals, so the
 * utilities are generated normally.
 *
 * Use FIELD for anything a person types or picks in; FIELD_SM for dense
 * toolbars; LABEL and HINT for the text around them.
 */

/** Standard input, select, and textarea. */
export const FIELD =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground transition-colors placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/40 disabled:cursor-not-allowed disabled:opacity-50";

/** Dense variant for filter bars and inline controls. */
export const FIELD_SM =
  "rounded-md border border-input bg-background px-2 py-1.5 text-xs text-foreground transition-colors placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/40 disabled:cursor-not-allowed disabled:opacity-50";

/** Monospace variant for identifiers, keys, and paths. */
export const FIELD_MONO = `${FIELD} font-mono`;

/** The label above a field. */
export const LABEL = "block text-sm font-medium text-foreground";

/** Helper or validation text below a field. */
export const HINT = "mt-1 text-xs text-muted-foreground";

/**
 * A checkbox or radio input.
 *
 * Eight spellings across ten call sites — `mt-0.5`, `mt-1`, `h-4 w-4`, nothing
 * at all, and one hardcoded indigo accent, which was the last raw palette
 * shade left in the app. It survived the Phase 7 sweep because the guard's
 * regex enumerated the property prefixes it knew about and `accent` was not
 * among them; `uniformity.test.ts` now matches the shade instead.
 *
 * The accent is the world's own CTA colour, as the drawer's theme radios
 * already did, so the control is themed by the same token as everything else
 * instead of being the one blue thing in a pink world.
 */
export const CHECKBOX =
  "size-4 shrink-0 accent-[var(--ttm-accent-cta)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

/**
 * The row a CHECKBOX sits in — the actual target, since a wrapping `<label>`
 * is what a pointer hits.
 *
 * A native checkbox renders at 13x13, under the 24x24 WCAG 2.5.8 minimum, and
 * cannot be resized without `appearance-none` and rebuilding the check glyph.
 * Sizing the row instead is the honest fix: the label is the target, so a
 * 44px row is a 44px target. Lifted from the drawer's theme picker, which
 * already established this as the house measurement in Phase 4.
 */
export const CHOICE_ROW =
  "flex min-h-11 w-full min-w-0 cursor-pointer items-center gap-2 rounded-md px-2 text-sm text-foreground transition-colors hover:bg-muted";

/**
 * Wrapper for a checkbox that has no visible label text — a bare "select this
 * row" box whose name comes from `aria-label`.
 *
 * CHOICE_ROW cannot help here because there is no row: the target is the 16px
 * box itself, under the 24px minimum. Equal padding and negative margin expand
 * the clickable area to 32px without moving the box a pixel or disturbing the
 * layout around it.
 */
export const CHECKBOX_HIT =
  "-m-2 flex shrink-0 cursor-pointer items-start p-2";

/**
 * A button that looks like a link — "Select all visible", "Clear filters".
 *
 * These rendered at 16px tall, well under the 24px minimum, because a bare
 * `<button>` around small text is only as tall as its line box. `min-h-9`
 * gives a real target without the visual weight of a bordered button, which is
 * the point of the affordance.
 */
export const LINK_BUTTON =
  "inline-flex min-h-9 items-center rounded-md text-xs font-medium text-primary-ink underline-offset-2 transition-colors hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

/**
 * LINK_BUTTON for the secondary action of a pair ("Clear" beside "Select
 * all"). Spelled out rather than derived from LINK_BUTTON by string surgery:
 * Tailwind finds classes by scanning source text, so a class assembled at
 * runtime is a class that may not exist in the stylesheet.
 */
export const LINK_BUTTON_MUTED =
  "inline-flex min-h-9 items-center rounded-md text-xs font-medium text-muted-foreground underline-offset-2 transition-colors hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

/**
 * Canonical panel surfaces.
 *
 * GLASS, NOT PAINT. Every panel here is 90% card over a backdrop blur rather
 * than a solid fill. The page now carries a blueprint grid on `body`, and an
 * opaque panel sitting on it is a card that has punched a hole in the paper —
 * ten percent of the ground showing through, blurred, is what makes the panel
 * read as resting ON the page instead of replacing a rectangle of it.
 *
 * The blur is what keeps that honest. Translucency alone would let the grid's
 * hard 1px ruling run straight under the text; blurring the backdrop turns it
 * into a wash, so the surface stays quiet enough to read on. Where a browser
 * does not support `backdrop-filter` the 90% fill degrades to very nearly the
 * old opaque panel, which is the correct fallback.
 *
 * The companion to `field.ts`, and the same problem one level up: Phase 7 of
 * the overhaul collapsed six spellings of one form control onto one, but the
 * *panel* — the bordered box almost every section is drawn in — was never
 * given a name. It converged on its own anyway. One spelling accounts for 67
 * of the ~90 uses:
 *
 *     rounded-xl border border-border bg-card p-4
 *
 * The rest are near-misses that drifted: `rounded-lg` next to `rounded-xl`,
 * `border-input` where the neighbouring card says `border-border`, `p-3` and
 * `p-5` and `p-8`, and five different opacities of the same accent wash. None
 * of that was a decision anybody made; it is what happens when a concept is a
 * convention rather than a constant.
 *
 * So these name the majority spelling rather than propose a new one — adopting
 * them is a no-op for the 67, and pulls the outliers into line.
 *
 * Plain string constants, not wrapper components, for the reason field.ts
 * gives: the elements keep their own props, refs, and handlers, and Tailwind
 * scans the literals so the utilities are generated normally.
 *
 * Compose with `cn()` when a caller needs to add layout:
 *
 *     <section className={cn(PANEL, "space-y-3")}>
 */

/**
 * The default section container: a card on the page background.
 *
 * Tighter vertically than horizontally, and a step tighter again on a phone.
 * Equal padding on all four sides reads as generous on one card and as waste
 * down a column of them — vertical space is what a reader scrolls through, and
 * 16px above and below every panel was most of a phone screen spent on
 * nothing. Horizontal padding is left alone: that is the measure the text
 * inside is set to.
 */
export const PANEL =
  "rounded-lg border border-panel-border bg-card/90 backdrop-blur-md px-3 py-2.5 sm:px-4 sm:py-3";

/**
 * PANEL with no padding of its own, for a card that draws its own divisions —
 * a titled header rule over a chart or a link list. The three visualization
 * cards had all spelled it out inline, one of them differently.
 */
export const PANEL_FLUSH =
  "rounded-lg border border-panel-border bg-card/90 backdrop-blur-md";

/** The titled header rule inside a PANEL_FLUSH card. */
export const PANEL_HEADER = "border-b border-border px-5 py-3";

/** The body of a PANEL_FLUSH card, under its header. */
export const PANEL_BODY = "p-4";

/**
 * A surface nested inside a PANEL — a scroll list, a sub-group, a preview.
 * One step down in radius and padding so nesting reads as depth rather than
 * as two cards that happen to touch.
 */
export const PANEL_INSET = "rounded-lg border border-border bg-background/90 backdrop-blur-md p-3";

/** A quieter panel for supporting detail that should recede. */
export const PANEL_MUTED =
  "rounded-lg border border-border bg-muted/40 px-4 py-3";

/**
 * Tonal panels, for a banner that carries a state. Each is the neutral PANEL
 * with its hue swapped in at the same weights — a 30% border on a 10% wash —
 * so the family reads as one component in five moods rather than five
 * components. Text inside these must use the blended `-ink` variants; the raw
 * status hue on a 10% wash of itself lands under AA (see index.css).
 */
export const PANEL_ACCENT =
  "rounded-lg border border-primary/30 bg-accent/40 px-4 py-3";
export const PANEL_SUCCESS =
  "rounded-lg border border-success/30 bg-success/10 px-4 py-3";
export const PANEL_WARNING =
  "rounded-lg border border-warning/30 bg-warning/10 px-4 py-3";
export const PANEL_DANGER =
  "rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3";

/**
 * A bounded, scrolling list of choices inside a panel.
 *
 * `min-w-0` is load-bearing and not cosmetic. A scroll container's default
 * `min-width: auto` resolves to its min-content width, so a list of long
 * facility names refuses to shrink, pushes its parent past the viewport, and
 * the whole page scrolls sideways — with the header and footer, honest
 * 100%-width bars, stopping short of the content. `overscroll-contain` keeps
 * a flick inside the list from scrolling the page once it bottoms out.
 */
export const SCROLL_LIST = `${PANEL_INSET} min-w-0 max-h-72 space-y-1 overflow-y-auto overscroll-contain p-1`;

/**
 * Canonical panel surfaces.
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

/** The default section container: a card on the page background. */
export const PANEL = "rounded-xl border border-border bg-card p-4";

/**
 * A surface nested inside a PANEL — a scroll list, a sub-group, a preview.
 * One step down in radius and padding so nesting reads as depth rather than
 * as two cards that happen to touch.
 */
export const PANEL_INSET = "rounded-lg border border-border bg-background p-3";

/** A quieter panel for supporting detail that should recede. */
export const PANEL_MUTED = "rounded-xl border border-border bg-muted/40 p-4";

/**
 * Tonal panels, for a banner that carries a state. Each is the neutral PANEL
 * with its hue swapped in at the same weights — a 30% border on a 10% wash —
 * so the family reads as one component in five moods rather than five
 * components. Text inside these must use the blended `-ink` variants; the raw
 * status hue on a 10% wash of itself lands under AA (see index.css).
 */
export const PANEL_ACCENT = "rounded-xl border border-primary/30 bg-accent/40 p-4";
export const PANEL_SUCCESS = "rounded-xl border border-success/30 bg-success/10 p-4";
export const PANEL_WARNING = "rounded-xl border border-warning/30 bg-warning/10 p-4";
export const PANEL_DANGER =
  "rounded-xl border border-destructive/30 bg-destructive/10 p-4";

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

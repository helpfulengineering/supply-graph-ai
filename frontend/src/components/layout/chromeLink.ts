/**
 * The one class list for a link in the page chrome's role lines — the hero
 * crumb and the breadcrumb trail.
 *
 * A dotted underline at rest rather than a colour change on hover: both lines
 * are a single muted run of text, so a link that only announces itself under a
 * cursor is invisible to anyone arriving by keyboard, and "hover to discover"
 * is not an affordance on a touch screen. The trail's links used to carry
 * `hover:text-primary-ink` alone and were indistinguishable from the text
 * beside them until touched.
 *
 * The `!` is load-bearing. index.css carries an unlayered
 * `a { text-decoration: none }`, and Tailwind v4 puts utilities in a cascade
 * layer — unlayered rules beat layered ones whatever their specificity, so a
 * plain `underline` class on an anchor computes to text-decoration-line: none.
 * The same is true of the other underline utilities on links in this app, which
 * is a fix for the reset's layer rather than for these two components.
 */
export const CHROME_LINK =
  "rounded-sm underline! decoration-dotted! underline-offset-4 hover:text-foreground hover:decoration-solid! focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

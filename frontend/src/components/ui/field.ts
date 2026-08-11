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

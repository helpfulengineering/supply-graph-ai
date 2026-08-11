/**
 * The event vocabulary, and the rule about what may go in it.
 *
 * Named here rather than as string literals at each call site because the
 * operator's Activity feed groups by this exact string: a typo does not fail a
 * build, it invents a second event type that looks real and never reconciles
 * with the first.
 *
 * WHAT IS WORTH RECORDING. A page view already says which design or facility
 * someone opened — those are routes. So a separate `design_open` would be the
 * same fact twice, and the events below are deliberately only the things a
 * path cannot tell you: that someone *did* something, and how it turned out.
 * "Ran a match against this design and got nothing back" is the sentence an
 * operator actually needs; no amount of page-view counting produces it.
 *
 * WHAT MAY NOT GO IN PROPS. No free text, ever — no search queries, no form
 * contents, no names. The identifiers here are public catalogue records (an
 * OKH design, an OKW facility), which is what this instance exists to serve
 * and is not personal data. Counts and outcomes are fine. The distinction is
 * not squeamishness: this schema attributes rows to a visitor_email, so a
 * props blob containing what someone typed would turn a usage counter into a
 * record of a named person's queries, which is a different product with
 * different obligations, and nobody opted into it.
 */

export const EVENTS = {
  /** A route was shown. `page` carries the path; props stay empty. */
  pageView: "page_view",
  /**
   * A match completed. The one action this app exists for, and the only place
   * an outcome exists to record — props carry how many solutions came back,
   * so an operator can see designs that consistently match nothing.
   */
  matchRun: "match_run",
  /** A match result was opened as a supply tree — did the match lead anywhere. */
  supplyTreeView: "supply_tree_view",
} as const;

export type EventName = (typeof EVENTS)[keyof typeof EVENTS];

/** Props for `match_run`. Counts and public ids only — see the file header. */
export interface MatchRunProps extends Record<string, unknown> {
  /** OKH id, or "inline" for a manifest pasted rather than picked. */
  design: string;
  /** How many solutions came back. Zero is the interesting case. */
  solutions: number;
  /** Which system mode ran. */
  mode: string;
  /** How many facilities the run was narrowed to; 0 means the whole network. */
  facilities: number;
}

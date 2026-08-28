/**
 * Aggregation over the activity rows the feed already holds.
 *
 * A reverse-chronological log answers "what happened last" and nothing else.
 * The questions an operator actually opens this page with — what is this
 * instance used for, which pages get reached, are matches finding anything —
 * are all counting questions, and counting a list you already fetched costs a
 * pass over an array rather than another round trip.
 *
 * Pure, so the thresholds and the tie-breaking are tested rather than
 * eyeballed against whatever the seed data happened to contain.
 */

import { EVENTS } from "./events";
import type { ActivityEntry } from "./rows";

export interface Tally {
  label: string;
  count: number;
}

export interface ActivitySummary {
  total: number;
  /** Event names by frequency, descending. */
  events: Tally[];
  /** Page paths by frequency, descending. Only page views count here. */
  pages: Tally[];
  /**
   * Match runs that returned nothing, out of all match runs seen.
   *
   * The single most useful number on the page and the reason `match_run`
   * carries its outcome: a design that never matches anything is invisible in
   * traffic — the run succeeded, the page rendered — and shows up only as a
   * count of empty results.
   */
  matchRuns: number;
  emptyMatchRuns: number;
  /**
   * Designs that were matched and came back with nothing, by how often.
   *
   * The one thing on this page an operator can act on. Every other number
   * describes what the instance did; this describes what it *failed* to do,
   * and names the capability gap: these are the things people came here to
   * make and this facility network cannot make. An operator recruiting
   * facilities wants exactly this list, and no amount of page-view counting
   * produces it — a match returning nothing renders a perfectly normal page.
   */
  unmetDemand: Tally[];
}

/** Descending by count, then by label so equal counts do not reorder at random. */
function rank(counts: Map<string, number>, limit: number): Tally[] {
  return [...counts]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
    .slice(0, limit);
}

function bump(counts: Map<string, number>, key: string): void {
  counts.set(key, (counts.get(key) ?? 0) + 1);
}

export function summarize(entries: ActivityEntry[], limit = 5): ActivitySummary {
  const events = new Map<string, number>();
  const pages = new Map<string, number>();
  const unmet = new Map<string, number>();
  let matchRuns = 0;
  let emptyMatchRuns = 0;

  for (const entry of entries) {
    if (!entry.event) continue;
    bump(events, entry.event);

    if (entry.event === EVENTS.pageView && entry.page) bump(pages, entry.page);

    if (entry.event === EVENTS.matchRun) {
      matchRuns += 1;
      // Absent props are not zero: the masked read does not return props at
      // all, and a row written before match_run carried an outcome has none.
      // Counting those as empty would invent failures that never happened.
      const solutions = entry.props?.solutions;
      if (typeof solutions === "number" && solutions === 0) {
        emptyMatchRuns += 1;
        const design = entry.props?.design;
        if (typeof design === "string" && design) bump(unmet, design);
      }
    }
  }

  return {
    total: entries.length,
    events: rank(events, limit),
    pages: rank(pages, limit),
    matchRuns,
    emptyMatchRuns,
    unmetDemand: rank(unmet, limit),
  };
}

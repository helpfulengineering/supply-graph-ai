/**
 * Timestamp formatting for the site layer's records.
 *
 * A telemetry feed is read for recency — "was anyone here in the last hour" —
 * so the list shows an age, and the exact instant goes in the `title` where a
 * hover or a screen reader can still reach it. Pure and injectable `now` so
 * the thresholds are tested rather than eyeballed against the wall clock.
 */

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/**
 * Coarse age of an ISO timestamp: "just now", "6m", "3h", "12d".
 *
 * Deliberately not `Intl.RelativeTimeFormat`: the strings here sit in a dense
 * column beside an event name, where "6 minutes ago" wraps and the unit
 * abbreviation does not. Returns an em dash for a missing or unparseable
 * timestamp, which is what a column with nothing in it should look like.
 */
export function age(iso: string | null, now: number = Date.now()): string {
  if (!iso) return "—";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "—";

  const delta = now - then;
  // A row written a moment ago can carry a timestamp a second or two ahead of
  // this clock; "in the future" is never the useful reading of that.
  if (delta < MINUTE) return "just now";
  if (delta < HOUR) return `${Math.floor(delta / MINUTE)}m`;
  if (delta < DAY) return `${Math.floor(delta / HOUR)}h`;
  return `${Math.floor(delta / DAY)}d`;
}

/**
 * `age` as a phrase, for prose that would otherwise read "just now ago".
 *
 * The dense feed wants the bare token in its own column; a sentence wants the
 * preposition. Putting the join here rather than in the markup keeps the two
 * spellings from disagreeing about the one case where "ago" does not apply.
 */
export function since(iso: string | null, now: number = Date.now()): string {
  const value = age(iso, now);
  return value === "just now" || value === "—" ? value : `${value} ago`;
}

/** The full instant, for the `title` behind an age. Empty when unparseable. */
export function instant(iso: string | null): string {
  if (!iso) return "";
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? "" : at.toLocaleString();
}

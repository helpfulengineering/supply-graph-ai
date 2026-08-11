/**
 * Row → domain mapping for the site layer's RPCs, and the tier-neutral shapes
 * Mission Control's panels render.
 *
 * Two jobs, both pure, so neither needs the Supabase SDK to be tested.
 *
 * 1. TRANSLATION. The RPCs return snake_case columns; the app speaks
 *    camelCase. Doing it here keeps the one place where a response shape is
 *    assumed to a handful of total functions over `unknown` — a row missing a
 *    column yields a usable record rather than throwing, because a schema one
 *    migration behind the client should cost a column, not the whole panel.
 *
 * 2. UNIFICATION. Each surface has two backing RPCs — a masked one any signed
 *    in visitor may call, and an unmasked operator one — returning different
 *    columns for the same thing. Mapping both onto one shape that carries its
 *    own `masked` flag means the directory and the activity feed are each a
 *    single component rendering a single type, instead of two near-identical
 *    components drifting apart. The flag is what the panels gate their
 *    mutations on, so an operator-only control cannot be rendered over
 *    self-service data by accident.
 *
 * See supabase/schema.sql for the tiers and the threat model they answer.
 */

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** Blank and absent are the same thing here: a column with nothing to show. */
function opt(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

/** A props blob, or null when absent — never `{}`, which reads as "empty". */
function props(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function rows(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function field(row: unknown, key: string): unknown {
  return row && typeof row === "object" ? (row as Record<string, unknown>)[key] : undefined;
}

/** A visitor's own record — the only row a visitor can read unmasked and edit. */
export interface OwnRecord {
  name: string;
  email: string;
  firstSeen: string | null;
  lastSeen: string | null;
  /** Display marker only. Operator access never derives from it. */
  isAdmin: boolean;
}

export function toOwnRecord(value: unknown): OwnRecord | null {
  // ohmgr_my_record returns a set, so an unknown email is an empty array
  // rather than a null row.
  const row = rows(value)[0] ?? (Array.isArray(value) ? undefined : value);
  const email = opt(field(row, "email"));
  if (!email) return null;
  return {
    name: str(field(row, "name")),
    email,
    firstSeen: opt(field(row, "first_seen")),
    lastSeen: opt(field(row, "last_seen")),
    isAdmin: field(row, "is_admin") === true,
  };
}

/** One row of the visitor directory, from either tier's RPC. */
export interface DirectoryEntry {
  name: string;
  /**
   * The address as this tier is allowed to see it: raw for an operator,
   * `f***@d***` for a signed-in visitor. Never both — the masked RPC does not
   * return the raw address at all, so there is nothing here to un-mask.
   */
  email: string;
  masked: boolean;
  /** Operator-only column; null on the masked read. */
  firstSeen: string | null;
  lastSeen: string | null;
  isAdmin: boolean;
}

export function toMaskedDirectory(value: unknown): DirectoryEntry[] {
  return rows(value).map((row) => ({
    name: str(field(row, "name")),
    email: str(field(row, "email_masked")),
    masked: true,
    firstSeen: null,
    lastSeen: opt(field(row, "last_seen")),
    isAdmin: field(row, "is_admin") === true,
  }));
}

export function toOperatorDirectory(value: unknown): DirectoryEntry[] {
  return rows(value).map((row) => ({
    name: str(field(row, "name")),
    email: str(field(row, "email")),
    masked: false,
    firstSeen: opt(field(row, "first_seen")),
    lastSeen: opt(field(row, "last_seen")),
    isAdmin: field(row, "is_admin") === true,
  }));
}

/** One telemetry event, from either tier's RPC. */
export interface ActivityEntry {
  ts: string | null;
  event: string;
  page: string | null;
  /** Operator-only column; null on the masked read. */
  sessionId: string | null;
  /** Raw address for an operator, `f***@d***` otherwise, "" if unattributed. */
  visitor: string;
  /**
   * The event's own payload — counts and public ids, per events.ts.
   *
   * Operator-only, and null rather than `{}` when absent: the masked read does
   * not select props at all, and a row written before an event carried an
   * outcome has none. A summary that read a missing payload as a zero would
   * report failures that never happened.
   */
  props: Record<string, unknown> | null;
  masked: boolean;
}

export function toMaskedActivity(value: unknown): ActivityEntry[] {
  return rows(value).map((row) => ({
    ts: opt(field(row, "ts")),
    event: str(field(row, "event")),
    page: opt(field(row, "page")),
    sessionId: null,
    visitor: str(field(row, "visitor_masked")),
    props: null,
    masked: true,
  }));
}

export function toOperatorActivity(value: unknown): ActivityEntry[] {
  return rows(value).map((row) => ({
    ts: opt(field(row, "ts")),
    event: str(field(row, "event")),
    page: opt(field(row, "page")),
    sessionId: opt(field(row, "session_id")),
    visitor: str(field(row, "visitor_email")),
    props: props(field(row, "props")),
    masked: false,
  }));
}

/** `ohmgr_admin_stats` returns a one-row set carrying the event count. */
export function toEventTotal(value: unknown): number {
  const row = rows(value)[0] ?? (Array.isArray(value) ? undefined : value);
  const total = field(row, "total_events");
  const n = typeof total === "string" ? Number(total) : total;
  return typeof n === "number" && Number.isFinite(n) ? n : 0;
}

/** `ohmgr_admin_purge_events` returns the deleted count as a bare bigint. */
export function toDeletedCount(value: unknown): number {
  const n = typeof value === "string" ? Number(value) : value;
  return typeof n === "number" && Number.isFinite(n) ? n : 0;
}

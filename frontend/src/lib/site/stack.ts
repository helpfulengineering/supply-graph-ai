"use client";

import { siteConfig } from "./config";
import {
  toDeletedCount,
  toEventTotal,
  toMaskedActivity,
  toMaskedDirectory,
  toOperatorActivity,
  toOperatorDirectory,
  toOwnRecord,
  type ActivityEntry,
  type DirectoryEntry,
  type OwnRecord,
} from "./rows";
// Type-only: erased at compile time, so the default build still ships no SDK.
import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * Site-layer client: visitor identity and batched telemetry.
 *
 * Ported from the reference's stack.js. Two properties carried over
 * deliberately:
 *
 * 1. FAIL-SOFT, FOR THE AMBIENT CALLS. Page-view telemetry, gate copy, and
 *    sign-in are no-ops when the layer is disabled, and their network failures
 *    are swallowed. Telemetry must never be able to break a page — the app's
 *    actual job is matching designs to facilities.
 * 2. NO SDK ON THE DEFAULT BUILD. The Supabase client is imported dynamically
 *    inside the enabled branch, so an instance that never opts in does not
 *    ship it at all. A static import would put it in every bundle to serve a
 *    capability that is off by default.
 *
 * WHAT IS NOT FAIL-SOFT: everything the Operator Tools panels call. Fail-soft
 * is right for a dropped page-view because nobody asked for it and nobody is
 * waiting on it. It is wrong for a read or a mutation somebody clicked: an
 * operator who deletes a visitor and gets silence cannot tell "deleted" from
 * "your token expired" from "the network is down", and will click again. So
 * those return a `Result` and the panels render the failure. The two idioms
 * live in one file because they talk to one schema — the distinction is who
 * asked, not which table.
 *
 * This is the SITE layer. It never grants application permissions — those come
 * from the backend's whoami. See supabase/schema.sql for the full boundary.
 */

const SESSION_KEY = "ohm_site_session";
const VISITOR_KEY = "ohm_site_visitor";
/**
 * sessionStorage, never local: the operator token is the site layer's only
 * real secret, and a tab-scoped hold means closing the tab locks it again.
 * Persisting it would turn "unlock for a moment" into a credential left on
 * the device.
 */
const OPERATOR_KEY = "ohm_site_operator";
const FLUSH_MS = 4000;
const MAX_BATCH = 25;

/**
 * One event as ohmgr_track reads it.
 *
 * The key names are the RPC's, not the client's: supabase/schema.sql reads
 * session_id / page / visitor_email and inserts them into columns of those
 * names. They are optional because an absent key stores NULL, while an empty
 * string stores an empty string — and the readers cannot tell the latter from
 * a real value.
 */
export interface TelemetryEvent {
  event: string;
  props: Record<string, unknown>;
  session_id?: string;
  page?: string;
  visitor_email?: string;
  ts: string;
}

export interface Visitor {
  name: string;
  email: string;
}

/**
 * The gate as the operator configured it (ohmgr_site_config, key 'gate').
 *
 * `enabled` is the operator's switch for presenting the gate at all; it is not
 * the layer's own on/off, which is siteConfig.enabled.
 */
export interface GateCopy {
  enabled: boolean;
  title: string;
  body: string;
  fine: string;
}

/**
 * Copy used when the operator has expressed no preference.
 *
 * The seeded config row carries empty strings, which mean "no preference"
 * rather than "render an empty heading" — so each field falls back on its own,
 * and an operator who sets only a title keeps the default body and fine print.
 */
export const GATE_DEFAULTS: GateCopy = {
  enabled: true,
  title: "Sign in to Operator Tools",
  body: "Operator Tools shows this site's own record of who visited and what they used. Sign in so your entry is yours: you can rename it, or erase it and everything attributed to it.",
  fine: "Site sign-in is unverified and stays on this device. It grants nothing in OHM — creating designs, editing facilities, and administration all come from your OHM API session, which this does not touch.",
};

let queue: TelemetryEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;

/**
 * Set when the backing schema is absent (the RPCs 404).
 *
 * "Fail-soft" has to mean the failure stops, not that it repeats quietly: a
 * project with the env vars set but supabase/schema.sql not yet run would
 * otherwise 404 on every batch, once per page view, forever — noisy in the
 * console and pointless on the wire. One 404 is enough to conclude the layer
 * is not provisioned, so the client goes dormant for the session.
 */
let schemaMissing = false;

function sessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    let id = sessionStorage.getItem(SESSION_KEY);
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem(SESSION_KEY, id);
    }
    return id;
  } catch {
    return "";
  }
}

function currentPath(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.location.pathname;
  } catch {
    return "";
  }
}

export function visitor(): Visitor | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(VISITOR_KEY);
    return raw ? (JSON.parse(raw) as Visitor) : null;
  } catch {
    return null;
  }
}

export function setVisitor(v: Visitor): void {
  try {
    localStorage.setItem(VISITOR_KEY, JSON.stringify(v));
  } catch {
    // ignore
  }
}

export function clearVisitor(): void {
  try {
    localStorage.removeItem(VISITOR_KEY);
  } catch {
    // ignore
  }
}

/**
 * One client per tab, created lazily.
 *
 * Memoised because the SDK warns — correctly — about multiple GoTrueClient
 * instances sharing a storage key, and a page view now makes three calls
 * (telemetry, gate copy, the operator probe). The promise is cached rather
 * than the client so concurrent callers share one dynamic import too.
 */
let clientPromise: Promise<SupabaseClient> | null = null;

async function client(): Promise<SupabaseClient | null> {
  if (!siteConfig.enabled) return null;
  // Dynamic so the SDK stays out of the default (disabled) bundle.
  clientPromise ??= import("@supabase/supabase-js").then(({ createClient }) =>
    createClient(siteConfig.url, siteConfig.anonKey),
  );
  return clientPromise;
}

export async function flush(): Promise<void> {
  if (!siteConfig.enabled || schemaMissing || queue.length === 0) return;
  const batch = queue.slice(0, MAX_BATCH);
  queue = queue.slice(batch.length);
  try {
    const sb = await client();
    const { error } = (await sb?.rpc("ohmgr_track", { p_events: batch })) ?? {};
    if (isMissingSchema(error)) {
      schemaMissing = true;
      queue = [];
    }
  } catch {
    // Fail-soft: a dropped telemetry batch is not worth surfacing.
  }
}

/** A 404/PGRST202 means the RPC does not exist, i.e. schema.sql was never run. */
function isMissingSchema(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const { code, message } = error as { code?: string; message?: string };
  return code === "PGRST202" || code === "404" || /not exist|not found/i.test(message ?? "");
}

export interface TelemetryContext {
  sessionId: string;
  page: string;
  visitor: Visitor | null;
  ts: string;
}

/**
 * Builds one wire event for ohmgr_track.
 *
 * `ts` is carried for ordering but the RPC ignores it — the column default
 * now() is authoritative, and flush latency is capped at FLUSH_MS, so a
 * client-supplied timestamp would buy four seconds of accuracy at the cost of
 * letting a client backdate rows.
 *
 * visitor_email is lowercased and trimmed to match how ohmgr_gate_signin
 * stores it. ohmgr_delete_own erases telemetry with `where visitor_email = e`,
 * so a row written in another case is a row "erase everything attributed to
 * me" silently misses.
 */
export function buildTelemetryEvent(
  event: string,
  props: Record<string, unknown>,
  ctx: TelemetryContext,
): TelemetryEvent {
  const e: TelemetryEvent = { event, props, ts: ctx.ts };
  if (ctx.sessionId) e.session_id = ctx.sessionId;
  if (ctx.page) e.page = ctx.page;
  const email = ctx.visitor?.email.trim().toLowerCase();
  if (email) e.visitor_email = email;
  return e;
}

export function track(event: string, props: Record<string, unknown> = {}): void {
  if (!siteConfig.enabled || schemaMissing) return;
  queue.push(
    buildTelemetryEvent(event, props, {
      sessionId: sessionId(),
      page: currentPath(),
      visitor: visitor(),
      ts: new Date().toISOString(),
    }),
  );
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => void flush(), FLUSH_MS);
}

/** Gate sign-in. Returns false when the layer is off or the call fails. */
export async function signIn(name: string, email: string): Promise<boolean> {
  if (!siteConfig.enabled) return false;
  try {
    const sb = await client();
    const { error } = (await sb?.rpc("ohmgr_gate_signin", {
      p_name: name,
      p_email: email,
      p_ua: navigator.userAgent,
    })) ?? { error: new Error("disabled") };
    if (error) return false;
    setVisitor({ name, email });
    return true;
  } catch {
    return false;
  }
}

/**
 * Reads the operator's gate copy, falling back field-by-field to the defaults.
 *
 * Fail-soft like everything else here: an unconfigured, unreachable, or
 * unprovisioned layer yields the default copy rather than an error, because a
 * gate that cannot render its heading should still be a gate.
 *
 * This reads the table directly rather than through an RPC — whitelabel config
 * is public by nature and is the one table with a select policy for anon.
 */
export async function gateCopy(): Promise<GateCopy> {
  if (!siteConfig.enabled || schemaMissing) return GATE_DEFAULTS;
  try {
    const sb = await client();
    if (!sb) return GATE_DEFAULTS;
    const { data, error } = await sb
      .from("ohmgr_site_config")
      .select("value")
      .eq("key", "gate")
      .maybeSingle();
    if (error || !data) return GATE_DEFAULTS;
    return mergeGateCopy((data as { value?: unknown }).value);
  } catch {
    return GATE_DEFAULTS;
  }
}

/** Applies a stored config value over the defaults, ignoring junk and blanks. */
function mergeGateCopy(value: unknown): GateCopy {
  if (!value || typeof value !== "object") return GATE_DEFAULTS;
  const stored = value as Partial<Record<keyof GateCopy, unknown>>;
  const text = (key: "title" | "body" | "fine"): string => {
    const v = stored[key];
    return typeof v === "string" && v.trim() !== "" ? v.trim() : GATE_DEFAULTS[key];
  };
  return {
    // Absent or malformed means on: the seeded row says the gate is on, and a
    // typo in one key should not quietly remove the sign-in path.
    enabled: stored.enabled !== false,
    title: text("title"),
    body: text("body"),
    fine: text("fine"),
  };
}

// ── operator token ──────────────────────────────────────────────────────────

export function operatorToken(): string {
  if (typeof window === "undefined") return "";
  try {
    return sessionStorage.getItem(OPERATOR_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setOperatorToken(token: string): void {
  try {
    sessionStorage.setItem(OPERATOR_KEY, token);
  } catch {
    // ignore
  }
}

export function clearOperatorToken(): void {
  try {
    sessionStorage.removeItem(OPERATOR_KEY);
  } catch {
    // ignore
  }
}

/**
 * Site-layer operator check — deliberately NOT named isAdmin.
 *
 * isAdmin is application authorization from the backend's whoami and decides
 * what you may DO in OHM. isOperator is site-layer only: who may see visitor
 * records and publish whitelabel config. Merging them would break the identity
 * ADR's promise of offline verification with no central authority, and would
 * leave RequireAdmin obeying two disagreeing truths.
 *
 * VERIFIED BY THE TOKEN, NOT BY THE MARKER. This used to answer from
 * `ohmgr_is_admin(email)`, which reads the `is_admin` column — and schema.sql
 * is explicit that the column is a display marker and "access never derives
 * from it client-side". It cannot: gate emails are unauthenticated, so anyone
 * who types a seeded operator's address at the gate would have been "operator
 * verified". That was harmless only while nothing was gated behind it, and
 * this file now gates unmasked PII behind it.
 *
 * So the check is a round trip: present the held token to a token-gated RPC
 * and see whether it raises. `ohmgr_admin_stats` is the probe because it is
 * stable, cheap, and the panel wants its answer anyway. The token never leaves
 * this tab, and it is the server that decides — the client only relays.
 */
export async function isOperator(): Promise<boolean> {
  const token = operatorToken();
  if (!token) return false;
  return (await adminStats(token)).ok;
}

// ── tiered reads and mutations (not fail-soft — see the file header) ────────

export type Result<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

/**
 * Postgres exception messages, in the operator's terms.
 *
 * The RPCs raise short, exact strings ('unauthorized', 'sign in first'); those
 * are the right thing for a function to raise and the wrong thing to put in
 * front of a person, who needs to know which of their two identities the
 * server just refused. Anything unrecognised passes through rather than being
 * flattened into "something went wrong" — an unmapped Postgres error is still
 * more informative than no error.
 */
function readable(error: unknown): string {
  const message =
    error && typeof error === "object" ? ((error as { message?: string }).message ?? "") : "";
  if (/unauthorized/i.test(message)) {
    return "That operator token was not accepted. Check it, or unlock again.";
  }
  if (/sign in first/i.test(message)) {
    return "Sign in at the gate first — this view is for signed-in visitors.";
  }
  if (/no such visitor/i.test(message)) {
    return "No visitor with that address. It may already have been erased.";
  }
  return message || "The site layer did not answer.";
}

/**
 * One RPC call, mapped to a Result.
 *
 * `map` runs only on success, so every caller below is a name, its arguments,
 * and the shape it expects — the error paths are not restated seven times.
 */
async function call<T>(
  fn: string,
  args: Record<string, unknown>,
  map: (data: unknown) => T,
): Promise<Result<T>> {
  if (!siteConfig.enabled) {
    return { ok: false, error: "The site layer is not configured on this instance." };
  }
  try {
    const sb = await client();
    if (!sb) return { ok: false, error: "The site layer is not configured on this instance." };
    const { data, error } = await sb.rpc(fn, args);
    if (error) {
      if (isMissingSchema(error)) {
        schemaMissing = true;
        return {
          ok: false,
          error: "The site layer's tables are missing — run supabase/schema.sql.",
        };
      }
      return { ok: false, error: readable(error) };
    }
    return { ok: true, data: map(data) };
  } catch {
    return { ok: false, error: "Could not reach the site layer." };
  }
}

// self-service tier: any visitor who completed the gate, keyed by their claim

export function myRecord(email: string): Promise<Result<OwnRecord | null>> {
  return call("ohmgr_my_record", { p_email: email }, toOwnRecord);
}

export function updateOwnName(email: string, name: string): Promise<Result<null>> {
  return call("ohmgr_update_own_name", { p_email: email, p_name: name }, () => null);
}

export function deleteOwn(email: string): Promise<Result<null>> {
  return call("ohmgr_delete_own", { p_email: email }, () => null);
}

export function visitorsMasked(email: string): Promise<Result<DirectoryEntry[]>> {
  return call("ohmgr_visitors_masked", { p_email: email }, toMaskedDirectory);
}

export function eventsMasked(email: string, limit = 200): Promise<Result<ActivityEntry[]>> {
  return call("ohmgr_events_masked", { p_email: email, p_limit: limit }, toMaskedActivity);
}

// operator tier: token-gated, unmasked, mutating

export function adminStats(token: string): Promise<Result<number>> {
  return call("ohmgr_admin_stats", { p_token: token }, toEventTotal);
}

export function adminVisitors(token: string): Promise<Result<DirectoryEntry[]>> {
  return call("ohmgr_admin_visitors", { p_token: token }, toOperatorDirectory);
}

export function adminEvents(token: string, limit = 200): Promise<Result<ActivityEntry[]>> {
  return call("ohmgr_admin_events", { p_token: token, p_limit: limit }, toOperatorActivity);
}

export function adminUpdateVisitor(
  token: string,
  email: string,
  changes: { name?: string; isAdmin?: boolean },
): Promise<Result<null>> {
  return call(
    "ohmgr_admin_update_visitor",
    {
      p_token: token,
      p_email: email,
      // Explicit nulls, not omissions: the RPC coalesces null onto the current
      // value, so "leave the name alone" and "no name argument" must be the
      // same call. Omitting a key would land on the SQL default, which is null
      // anyway — sending it says so rather than relying on that.
      p_name: changes.name ?? null,
      p_is_admin: changes.isAdmin ?? null,
    },
    () => null,
  );
}

export function adminDeleteVisitor(token: string, email: string): Promise<Result<null>> {
  return call("ohmgr_admin_delete_visitor", { p_token: token, p_email: email }, () => null);
}

/** Deletes events older than `keepDays`, returning how many rows went. */
export function adminPurgeEvents(token: string, keepDays: number): Promise<Result<number>> {
  return call(
    "ohmgr_admin_purge_events",
    { p_token: token, p_keep_days: keepDays },
    toDeletedCount,
  );
}

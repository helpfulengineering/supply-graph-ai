"use client";

import { siteConfig } from "./config";
// Type-only: erased at compile time, so the default build still ships no SDK.
import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * Site-layer client: visitor identity and batched telemetry.
 *
 * Ported from the reference's stack.js. Two properties carried over
 * deliberately:
 *
 * 1. FAIL-SOFT. Every call is a no-op when the layer is disabled, and network
 *    failures are swallowed. Telemetry must never be able to break a page —
 *    the app's actual job is matching designs to facilities.
 * 2. NO SDK ON THE DEFAULT BUILD. The Supabase client is imported dynamically
 *    inside the enabled branch, so an instance that never opts in does not
 *    ship it at all. A static import would put it in every bundle to serve a
 *    capability that is off by default.
 *
 * This is the SITE layer. It never grants application permissions — those come
 * from the backend's whoami. See supabase/schema.sql for the full boundary.
 */

const SESSION_KEY = "ohm_site_session";
const VISITOR_KEY = "ohm_site_visitor";
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
  title: "Sign in to Mission Control",
  body: "Mission Control shows this site's own record of who visited and what they used. Sign in so your entry is yours: you can rename it, or erase it and everything attributed to it.",
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

/**
 * Site-layer operator check — deliberately NOT named isAdmin.
 *
 * isAdmin is application authorization from the backend's whoami and decides
 * what you may DO in OHM. isOperator is site-layer only: who may see visitor
 * records and publish whitelabel config. Merging them would break the identity
 * ADR's promise of offline verification with no central authority, and would
 * leave RequireAdmin obeying two disagreeing truths.
 */
export async function isOperator(): Promise<boolean> {
  if (!siteConfig.enabled || schemaMissing) return false;
  const v = visitor();
  if (!v?.email) return false;
  try {
    const sb = await client();
    const { data } = (await sb?.rpc("ohmgr_is_admin", { p_email: v.email })) ?? {
      data: false,
    };
    return data === true;
  } catch {
    return false;
  }
}

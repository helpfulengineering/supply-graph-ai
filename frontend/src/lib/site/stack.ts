"use client";

import { siteConfig } from "./config";

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

interface TelemetryEvent {
  event: string;
  props: Record<string, unknown>;
  session: string;
  ts: string;
}

export interface Visitor {
  name: string;
  email: string;
}

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

async function client() {
  if (!siteConfig.enabled) return null;
  // Dynamic so the SDK stays out of the default (disabled) bundle.
  const { createClient } = await import("@supabase/supabase-js");
  return createClient(siteConfig.url, siteConfig.anonKey);
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

export function track(event: string, props: Record<string, unknown> = {}): void {
  if (!siteConfig.enabled || schemaMissing) return;
  queue.push({ event, props, session: sessionId(), ts: new Date().toISOString() });
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

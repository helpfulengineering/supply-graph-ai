import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../../test/msw/server";
import { buildTelemetryEvent, type TelemetryContext, type Visitor } from "./stack";

function context(overrides: Partial<TelemetryContext> = {}): TelemetryContext {
  return {
    sessionId: "sess-1",
    page: "/designs",
    visitor: null,
    ts: "2026-08-11T00:00:00.000Z",
    ...overrides,
  };
}

function person(overrides: Partial<Visitor> = {}): Visitor {
  return { name: "Ada", email: "ada@example.com", ...overrides };
}

describe("buildTelemetryEvent", () => {
  it("emits the key names ohmgr_track reads, not the client's", () => {
    const e = buildTelemetryEvent("page_view", {}, context({ visitor: person() }));
    expect(Object.keys(e).sort()).toEqual([
      "event",
      "page",
      "props",
      "session_id",
      "ts",
      "visitor_email",
    ]);
  });

  it("lowercases and trims visitor_email so ohmgr_delete_own matches these rows", () => {
    const e = buildTelemetryEvent(
      "page_view",
      {},
      context({ visitor: person({ email: "  Ada@Example.COM " }) }),
    );
    expect(e.visitor_email).toBe("ada@example.com");
  });

  it("omits empty fields rather than sending empty strings", () => {
    const e = buildTelemetryEvent("page_view", {}, context({ sessionId: "", page: "" }));
    expect(e).not.toHaveProperty("session_id");
    expect(e).not.toHaveProperty("page");
    expect(e).not.toHaveProperty("visitor_email");
  });

  it("passes props through untouched", () => {
    const props = { kind: "okh", nested: { n: 1 } };
    expect(buildTelemetryEvent("opened", props, context()).props).toEqual(props);
  });

  it("always carries event and ts", () => {
    const e = buildTelemetryEvent("opened", {}, context());
    expect(e.event).toBe("opened");
    expect(e.ts).toBe("2026-08-11T00:00:00.000Z");
  });
});

/**
 * The layer reads its env at module load, so an enabled instance has to be a
 * fresh import under stubbed env. This is also the only test that exercises
 * the real supabase-js client, i.e. the only proof that `p_events` reaches the
 * wire shaped the way buildTelemetryEvent assumes.
 */
async function enabledStack(): Promise<typeof import("./stack")> {
  vi.stubEnv("NEXT_PUBLIC_OHM_SUPABASE_URL", "https://test.supabase.co");
  vi.stubEnv("NEXT_PUBLIC_OHM_SUPABASE_ANON_KEY", "anon-test-key");
  vi.resetModules();
  return import("./stack");
}

describe("flush", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("posts p_events with the RPC's key names", async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post("*/rest/v1/rpc/ohmgr_track", async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(null);
      }),
    );

    const stack = await enabledStack();
    stack.track("page_view");
    await stack.flush();

    expect(bodies).toHaveLength(1);
    const { p_events } = bodies[0] as { p_events: Array<Record<string, unknown>> };
    expect(p_events).toHaveLength(1);
    expect(p_events[0].event).toBe("page_view");
    expect(p_events[0].session_id).toEqual(expect.any(String));
    expect(p_events[0].page).toBe("/");
    expect(p_events[0]).not.toHaveProperty("session");
  });

  it("goes dormant after a PGRST202, so an unprovisioned project 404s once", async () => {
    let calls = 0;
    server.use(
      http.post("*/rest/v1/rpc/ohmgr_track", () => {
        calls += 1;
        return HttpResponse.json(
          { code: "PGRST202", message: "Could not find the function" },
          { status: 404 },
        );
      }),
    );

    const stack = await enabledStack();
    stack.track("page_view");
    await stack.flush();
    expect(calls).toBe(1);

    stack.track("page_view");
    await stack.flush();
    expect(calls).toBe(1);
  });
});

/**
 * The tiered calls, on the wire.
 *
 * Mission Control's panels mock this module wholesale, so nothing there
 * notices if an argument is misnamed — and these are `SECURITY DEFINER`
 * functions with fixed parameter names, where `p_email` spelled `email` is not
 * a rename but an RPC that raises. Same reasoning as the telemetry contract
 * above, applied to the twelve functions the operator views call.
 */
describe("tiered calls", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  /** Captures one RPC's request body and answers with `reply`. */
  function capture(
    fn: string,
    reply: Parameters<typeof HttpResponse.json>[0],
    status = 200,
  ) {
    const bodies: Array<Record<string, unknown>> = [];
    server.use(
      http.post(`*/rest/v1/rpc/${fn}`, async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(reply, { status });
      }),
    );
    return bodies;
  }

  it("sends the operator token under the name the RPC declares", async () => {
    const bodies = capture("ohmgr_admin_visitors", [
      {
        name: "Ada Lovelace",
        email: "ada@example.org",
        first_seen: "2026-08-01T09:00:00.000Z",
        last_seen: "2026-08-11T09:00:00.000Z",
        is_admin: true,
      },
    ]);

    const stack = await enabledStack();
    const result = await stack.adminVisitors("the-token");

    expect(bodies[0]).toEqual({ p_token: "the-token" });
    expect(result.ok).toBe(true);
    if (result.ok) {
      // Mapped to the domain shape, and marked unmasked so the panel may
      // render its mutations.
      expect(result.data[0]).toMatchObject({ email: "ada@example.org", masked: false });
    }
  });

  it("sends an explicit null for the field a marker toggle leaves alone", async () => {
    const bodies = capture("ohmgr_admin_update_visitor", null);

    const stack = await enabledStack();
    await stack.adminUpdateVisitor("the-token", "ada@example.org", { isAdmin: true });

    // ohmgr_admin_update_visitor coalesces null onto the current value, so
    // "leave the name alone" must arrive as p_name: null rather than as an
    // absent key or an empty string — the latter would fail its length check.
    expect(bodies[0]).toEqual({
      p_token: "the-token",
      p_email: "ada@example.org",
      p_name: null,
      p_is_admin: true,
    });
  });

  it("keeps the self-service reads keyed by the claimed email", async () => {
    const bodies = capture("ohmgr_events_masked", []);

    const stack = await enabledStack();
    await stack.eventsMasked("ada@example.org", 50);

    expect(bodies[0]).toEqual({ p_email: "ada@example.org", p_limit: 50 });
  });

  it("turns a raised 'unauthorized' into something an operator can act on", async () => {
    capture("ohmgr_admin_stats", { code: "P0001", message: "unauthorized" }, 400);

    const stack = await enabledStack();
    const result = await stack.adminStats("wrong");

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/token was not accepted/i);
  });

  it("reads a bigint total that PostgREST returned as a string", async () => {
    capture("ohmgr_admin_stats", [{ total_events: "128000" }]);

    const stack = await enabledStack();
    const result = await stack.adminStats("the-token");

    expect(result).toEqual({ ok: true, data: 128_000 });
  });

  it("is not an operator without a token, and never asks the server", async () => {
    let calls = 0;
    server.use(
      http.post("*/rest/v1/rpc/ohmgr_admin_stats", () => {
        calls += 1;
        return HttpResponse.json([{ total_events: "1" }]);
      }),
    );

    const stack = await enabledStack();
    expect(await stack.isOperator()).toBe(false);
    expect(calls).toBe(0);
  });

  it("establishes operator status by presenting the held token, not by is_admin", async () => {
    const bodies = capture("ohmgr_admin_stats", [{ total_events: "1" }]);

    const stack = await enabledStack();
    stack.setOperatorToken("the-token");

    expect(await stack.isOperator()).toBe(true);
    // The probe is the token-gated RPC. Nothing reads ohmgr_is_admin: gate
    // emails are unauthenticated, so a column anyone can claim cannot be the
    // credential. See supabase/schema.sql.
    expect(bodies[0]).toEqual({ p_token: "the-token" });

    stack.clearOperatorToken();
    expect(await stack.isOperator()).toBe(false);
  });
});

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

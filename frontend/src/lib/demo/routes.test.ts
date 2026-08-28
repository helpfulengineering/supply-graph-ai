import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { resolveDemoRoute } from "./routes";
import { demoOkhList, demoOkwSearch } from "./world";

/**
 * The demo world answers every question the app can ask.
 *
 * The first two suites are the gate, and they are written against the source
 * rather than against a list somebody remembered to update: `src/api/ohm/*.ts`
 * is where every path the app requests is spelled, so the paths are read out of
 * those files and each one is put to the demo router. A new endpoint added
 * without a demo answer fails here rather than as an empty page on the hosted
 * demo, which is how /rfq, /match and half of /settings came to be blank with
 * "Demo data" on and nothing in the console to say why.
 *
 * The third suite is the part a path list cannot check: that what comes back
 * is the SEEDED catalogue where a seeded catalogue exists, so the toggle and
 * `make seed-demo` agree, and that ids are honoured rather than every detail
 * page showing the same record.
 */

const API_DIR = join(import.meta.dirname, "..", "..", "api", "ohm");

/**
 * One source literal, reduced to the path the server sees.
 *
 * Three shapes turn up: a plain `"/api/okh"`, a client template with a typed
 * placeholder (`"/api/okh/{id}"`), and a hand-built template literal, where an
 * interpolation is either a path segment (`/reputation/${did}`) or a query
 * string glued to the end (`bindings${q}`). Only the first of those is part of
 * the path; the second is not, and treating it as one invents a route.
 *
 * Returns "" for anything that is prose rather than a route.
 */
function normalizeDeclaredPath(literal: string): string {
  if (literal.includes("...")) return "";
  const withoutQuery = literal.replace(/\?.*$/, "");
  const segments = withoutQuery.split("/").map((segment) => {
    if (!segment.includes("${")) return segment;
    // A whole segment that is one interpolation is an id; anything else is a
    // fragment appended to a real segment, and the path ends before it.
    return /^\$\{[^}]*\}$/.test(segment) ? "{param}" : segment.split("${")[0];
  });
  return segments.filter((segment, i) => i === 0 || segment !== "").join("/");
}

/**
 * Every `/api/...` path literal in the API layer, with the client's `{param}`
 * placeholders filled in.
 *
 * Read from the files rather than maintained by hand for the reason the
 * responsive lane gives about its route list: a list that has to be remembered
 * is a list that goes stale, and a stale one here would pass by not asking.
 */
function declaredApiPaths(): string[] {
  const paths = new Set<string>();
  for (const file of readdirSync(API_DIR)) {
    if (!file.endsWith(".ts") || file.endsWith(".test.ts")) continue;
    const source = readFileSync(join(API_DIR, file), "utf8");
    // Quoted or backticked, and the backticked ones interpolate: an id becomes
    // `{param}`, and a trailing query string is not part of the path at all.
    for (const match of source.matchAll(/["'`](\/api\/[^"'`\n]*)["'`]/g)) {
      const path = normalizeDeclaredPath(match[1]);
      if (path) paths.add(path);
    }
  }
  return [...paths];
}

/** Substitute a plausible id for each `{placeholder}`, and add the /v1 mount. */
function concrete(path: string): string {
  return `/v1${path}`
    .replace("{id}", "okh-0001")
    .replace("{job_id}", "job-1")
    .replace("{did}", "did:key:z6Mktest")
    .replace("{key_id}", "key-1")
    .replace("{account_id}", "acct-1")
    .replace("{grant_id}", "grant-1")
    .replace("{solution_id}", "sol-1")
    .replace("{param}", "did:key:z6Mktest");
}

/**
 * Paths the app only ever writes to. They are expected to refuse, not to
 * answer — see READ_ONLY in routes.ts — so they are checked separately.
 */
const WRITE_ONLY = [
  // Moving a package between this node and a remote store. The demo has no
  // remote, and pretending a push succeeded would be a lie about where the
  // bytes went.
  // Moves bytes between nodes; the demo has no peer to move them from.
  "/api/federation/packages/fetch",
  "/api/package/push",
  "/api/package/pull",
  // Conversions. Nothing is stored, but they are still POSTs that transform a
  // payload the caller supplied — the demo world has no file to convert, and
  // answering with a canned manifest would claim a conversion that never ran.
  "/api/convert/to-datasheet",
  "/api/convert/from-okh-losh",
  "/api/convert/from-datasheet",
  "/api/okh/create",
  "/api/okw/create",
  "/api/identity/spaces/claim",
  "/api/identity/attestations/certify",
  "/api/identity/bindings/domain",
  "/api/identity/bindings/domain/verify",
  "/api/identity/bindings/oauth",
  "/api/identity/accounts/{account_id}/disable",
  "/api/identity/identities/{did}/rotate",
  "/api/identity/keys/{key_id}",
  "/api/identity/grants/{grant_id}",
  "/api/identity/grants/bootstrap-edge",
  // Spelled {provider} rather than {param} since llm.ts moved onto the typed
  // client: the generated paths carry the parameter's real name, where a
  // template literal only ever showed an interpolation.
  "/api/llm/credentials/{provider}",
  "/api/llm/credentials/{provider}/test",
  "/api/federation/peers/discover",
  "/api/federation/peers/{did}/follow",
  "/api/federation/sync/run",
  "/api/federation/okw/sync/run",
  "/api/okh/generate-from-url/jobs/{job_id}/revoke",
];

describe("the demo world answers every route", () => {
  it("actually finds the API surface, so the gate cannot pass by asking nothing", () => {
    // The failure mode of a source-scanning test: tighten the pattern, extract
    // zero paths, and every assertion below passes vacuously. 40 is well under
    // the ~48 currently declared and well over anything a broken regex returns.
    expect(declaredApiPaths().length).toBeGreaterThan(40);
  });

  it("has data for every path the API layer declares", () => {
    const unanswered = declaredApiPaths()
      .filter((path) => !WRITE_ONLY.includes(path))
      .map((path) => concrete(path))
      .filter((path) => {
        const get = resolveDemoRoute("GET", path);
        const post = resolveDemoRoute("POST", path);
        return get.kind !== "json" && post.kind !== "json";
      });

    expect(
      unanswered,
      "these paths have no demo data — add them to routes.ts or to fixturesByPath",
    ).toEqual([]);
  });

  it("never falls through to the network for an API path", () => {
    // Falling through is right for a static asset and wrong for the API: on a
    // hosted demo there is no instance behind it, so the request resolves to
    // the origin's HTML and fails as a JSON parse error rather than as
    // anything a reader could interpret.
    for (const path of declaredApiPaths().map(concrete)) {
      expect(resolveDemoRoute("GET", path).kind, path).not.toBe("passthrough");
      expect(resolveDemoRoute("DELETE", path).kind, path).not.toBe(
        "passthrough",
      );
    }
  });

  it("refuses writes in the app's own words rather than failing obscurely", () => {
    const result = resolveDemoRoute("POST", "/v1/api/okh/create");
    expect(result.kind).toBe("error");
    if (result.kind !== "error") return;
    // 403 so `userFacingError` reaches its "Not allowed" branch, which is the
    // wording a permission failure gets against a real instance.
    expect(result.status).toBe(403);
    expect(result.detail).toMatch(/read-only/i);
  });

  it("leaves anything outside the API alone", () => {
    expect(resolveDemoRoute("GET", "/docs/index.html").kind).toBe(
      "passthrough",
    );
  });
});

describe("the demo world is the seeded world", () => {
  it("serves the seeded catalogue, not the test fixture, where both exist", () => {
    const list = resolveDemoRoute("GET", "/v1/api/okh");
    expect(list.kind).toBe("json");
    if (list.kind !== "json") return;
    expect(list.body).toBe(demoOkhList);

    const search = resolveDemoRoute("GET", "/v1/api/okw/search");
    if (search.kind !== "json") throw new Error("no okw search");
    expect(search.body).toBe(demoOkwSearch);
  });

  it("serves the seeded record for a seeded id", () => {
    const seededId = demoOkhList.items[0].id;
    const detail = resolveDemoRoute("GET", `/v1/api/okh/${seededId}`);
    if (detail.kind !== "json") throw new Error("no okh detail");
    expect((detail.body as { id: string }).id).toBe(seededId);
    expect((detail.body as { title: string }).title).toBe(
      demoOkhList.items[0].title,
    );
  });

  it("honours the id for an unseeded record instead of substituting another", () => {
    // The failure this pins: returning the fixture verbatim meant /okh/anything
    // rendered "Open Ventilator" under a URL that says otherwise, and a
    // visitor following two links landed on the same page twice.
    const detail = resolveDemoRoute("GET", "/v1/api/okh/not-in-the-world");
    if (detail.kind !== "json") throw new Error("no okh detail");
    expect((detail.body as { id: string }).id).toBe("not-in-the-world");
  });

  it("answers a supply tree for whichever solution a match produced", () => {
    for (const id of ["sol-1", "sol-99"]) {
      const viz = resolveDemoRoute(
        "GET",
        `/v1/api/supply-tree/solution/${id}/visualization`,
      );
      expect(viz.kind, id).toBe("json");
    }
  });

  it("answers the POSTs that are queries, so match and validation work", () => {
    for (const path of [
      "/v1/api/match",
      "/v1/api/match/facility",
      "/v1/api/okh/validate",
      "/v1/api/okw/validate",
    ]) {
      expect(resolveDemoRoute("POST", path).kind, path).toBe("json");
    }
  });

  it("hands back a finished generation job, since the demo has no worker", () => {
    const status = resolveDemoRoute(
      "GET",
      "/v1/api/okh/generate-from-url/jobs/demo-job-1",
    );
    if (status.kind !== "json") throw new Error("no job status");
    const body = status.body as { state: string; manifest: unknown };
    expect(body.state).toBe("SUCCESS");
    expect(body.manifest).toBeTruthy();
  });
});

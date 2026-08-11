import {
  attestationsFixture,
  disclosureFixture,
  disclosurePreviewFixture,
  facilityDesignsFixture,
  fixturesByPath,
  identityFixture,
  matchResponseFixture,
  okhDetailFixture,
  okwDetailFixture,
  packageMetadataFixture,
  provenanceFixture,
  validationResultFixture,
  visibilityFixture,
  vizBundleFixture,
} from "../../test/fixtures";
import {
  demoNetworkSpaces,
  demoOkhDetail,
  demoOkhList,
  demoOkwDetail,
  demoOkwSearch,
} from "./world";

/**
 * Which request the demo world answers, and with what.
 *
 * Split out of `demoFetch.ts` because the routing is the part with decisions in
 * it and the installer is four lines of plumbing. A pure `(method, pathname) →
 * result` function can be asserted route by route without replacing
 * `globalThis.fetch`, which is what makes the coverage test in `routes.test.ts`
 * possible: it walks every path the app can request and fails if one of them
 * would fall through to a network that, in a demo, is not there.
 *
 * That test is the point of this module. The previous table covered the six
 * endpoints the catalogue pages needed and let everything else through to the
 * real API, which is correct on an instance that has data and silently empty on
 * the hosted demo — a visitor toggling "Demo data" got a full dashboard, a full
 * catalogue, and then a spinner-then-error on /rfq, /match, and every settings
 * subtab. Demo mode is a data SOURCE, and a source that answers two thirds of
 * the questions is a worse lie than one that answers none.
 *
 * Three layers, in order:
 *
 *   1. The seeded world (`world.ts`), generated from scripts/seed_demo_data.py,
 *      so the toggle and `make seed-demo` show the same catalogue.
 *   2. The fixture world (`test/fixtures`), which the mocked Playwright lane and
 *      the MSW unit tests already run against — the settings, identity,
 *      package, and supply-tree surfaces the seed dataset has no opinion about.
 *      Sharing it is deliberate: demo data and test data drifting apart is how
 *      a lane goes green against a world nobody can see.
 *   3. Parameterised routes, which cannot be table keys, resolved below.
 */

/** What the demo source decided to do with a request. */
export type DemoRoute =
  | { kind: "json"; body: unknown }
  | { kind: "error"; status: number; detail: string }
  | { kind: "passthrough" };

const json = (body: unknown): DemoRoute => ({ kind: "json", body });

/**
 * The seeded catalogue, which takes precedence over the fixture of the same
 * path — `world.ts` is what an operator running `make seed-demo` will see.
 */
const SEEDED: Record<string, unknown> = {
  "/v1/api/okh": demoOkhList,
  "/v1/api/okw/search": demoOkwSearch,
  "/v1/api/okw/spaces": demoNetworkSpaces,
};

/**
 * Reads that carry an id, matched in order.
 *
 * Each returns `undefined` to mean "not my route" so the list can be walked;
 * returning a body for an unknown id is deliberate where the record's identity
 * does not change the shape of the answer (a provenance trail, a disclosure
 * preview). Where it does — an OKH detail — the seeded record is preferred and
 * the fixture is re-badged with the requested id rather than handing back
 * somebody else's title under this URL.
 */
const PARAMETERISED: Array<{
  method: "GET" | "POST";
  pattern: RegExp;
  resolve: (id: string) => unknown;
}> = [
  {
    method: "GET",
    pattern: /^\/v1\/api\/okh\/([^/]+)$/,
    resolve: (id) =>
      (demoOkhDetail as Record<string, unknown>)[id] ?? {
        ...okhDetailFixture,
        id,
      },
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/okh\/([^/]+)\/provenance$/,
    resolve: () => provenanceFixture,
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/okh\/([^/]+)\/visibility$/,
    resolve: (id) => ({ ...visibilityFixture, id }),
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/okw\/([^/]+)$/,
    resolve: (id) =>
      (demoOkwDetail as Record<string, unknown>)[id] ?? {
        ...okwDetailFixture,
        id,
      },
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/okw\/([^/]+)\/provenance$/,
    resolve: () => provenanceFixture,
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/okw\/([^/]+)\/visibility$/,
    resolve: (id) => ({ ...visibilityFixture, id }),
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/okw\/([^/]+)\/disclosure$/,
    resolve: () => disclosureFixture,
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/okw\/([^/]+)\/disclosure\/preview$/,
    resolve: () => disclosurePreviewFixture,
  },
  {
    method: "GET",
    // Any solution id: a supply tree is a match result, and in the demo every
    // match returns the one bundled solution, so every id is that solution.
    pattern: /^\/v1\/api\/supply-tree\/solution\/([^/]+)\/visualization$/,
    resolve: () => vizBundleFixture,
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/identity\/reputation\/(.+)$/,
    resolve: () => attestationsFixture,
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/identity\/identities\/([^/]+)$/,
    resolve: (did) => ({ ...identityFixture, did: decodeURIComponent(did) }),
  },
  {
    method: "GET",
    // org/project/version — three segments, one package.
    pattern: /^\/v1\/api\/package\/[^/]+\/[^/]+\/[^/]+$/,
    resolve: () => packageMetadataFixture,
  },
  {
    method: "GET",
    pattern: /^\/v1\/api\/okh\/generate-from-url\/jobs\/([^/]+)$/,
    resolve: (jobId) => finishedGenerateJob(jobId),
  },
];

/**
 * Requests that are POSTs for payload-size reasons rather than because they
 * change anything — a match, a validation, a facility's buildable designs.
 * These have to answer, or /match, /rfq and both validators are dead in demo
 * mode even though nothing about them writes.
 */
const QUERY_POSTS: Record<string, unknown> = {
  "/v1/api/match": matchResponseFixture,
  "/v1/api/match/facility": facilityDesignsFixture,
  "/v1/api/okh/validate": validationResultFixture,
  "/v1/api/okw/validate": validationResultFixture,
};

/**
 * A generation job that is already done.
 *
 * Demo mode has no worker and no repository to read, and a job that sat at
 * "Queued" forever would be a worse demonstration of the feature than not
 * offering it. `SUCCESS` with a manifest lets a visitor walk the whole review
 * step, which is the part of /okh/generate worth showing.
 */
function finishedGenerateJob(jobId: string): unknown {
  return {
    job_id: jobId,
    state: "SUCCESS",
    stage: "quality",
    fraction: 1,
    message: "Generated from the demo world",
    url: "https://github.com/demo/open-ventilator",
    manifest: okhDetailFixture,
    quality_report: {
      overall_quality: "good",
      required_fields_complete: true,
      missing_required_fields: [],
      recommendations: [
        "Add a bill of materials to raise this manifest to complete.",
      ],
    },
  };
}

/**
 * The one thing the demo cannot fake.
 *
 * A create, a revoke, a key rotation — these have no meaning without a server
 * to hold the result, and the honest failure is to say so. Answering 200 to a
 * write would leave a visitor looking at a list that did not change, which
 * reads as a bug in the product rather than as a limit of the demo; falling
 * through to the network answers with whatever the origin says, which on a
 * static demo host is an HTML 404 parsed as JSON.
 *
 * 403 rather than 501: `userFacingError` maps it to "Not allowed" with prose,
 * and the detail below replaces its body — so a write in demo mode surfaces
 * through exactly the same error path as a permission failure against a real
 * instance, in the app's own words.
 */
const READ_ONLY: DemoRoute = {
  kind: "error",
  status: 403,
  detail:
    "Demo data is a read-only sample world. Switch demo data off and connect to an instance to make changes.",
};

/**
 * Resolve one request against the demo world.
 *
 * `pathname` is the path only — query strings are ignored, because every
 * paginated and filtered list in the demo returns the same bundled page.
 */
export function resolveDemoRoute(method: string, pathname: string): DemoRoute {
  const verb = method.toUpperCase();

  if (verb === "GET" || verb === "HEAD") {
    if (pathname in SEEDED) return json(SEEDED[pathname]);
    const fixture = fixturesByPath[pathname];
    if (fixture !== undefined) return json(fixture);
  }

  for (const route of PARAMETERISED) {
    if (route.method !== verb) continue;
    const match = pathname.match(route.pattern);
    if (match) return json(route.resolve(match[1] ?? ""));
  }

  if (verb === "POST" && pathname in QUERY_POSTS) {
    return json(QUERY_POSTS[pathname]);
  }

  // Submitting a generation batch is a write in name only — nothing persists,
  // and the job it returns is already finished.
  if (verb === "POST" && pathname === "/v1/api/okh/generate-from-url/jobs") {
    return json({
      batch_id: "demo-batch",
      jobs: [
        {
          job_id: "demo-job-1",
          url: "https://github.com/demo/open-ventilator",
        },
      ],
    });
  }
  if (verb === "POST" && pathname === "/v1/api/okh/generate-from-url") {
    return json({
      success: true,
      message: "Generated from the demo world",
      manifest: okhDetailFixture,
      quality_report: {
        overall_quality: "good",
        required_fields_complete: true,
      },
    });
  }

  // Anything else under the API is a genuine mutation.
  if (pathname.startsWith("/v1/api/")) return READ_ONLY;

  return { kind: "passthrough" };
}

#!/usr/bin/env node
/**
 * `/v1` proxy contract test (Slice 0 of the frontend revamp integration — see
 * notes/frontend-revamp-integration-plan.md).
 *
 * The incoming fork deletes deploy/nginx.conf.template and reimplements every
 * guarantee it held as Next.js route handlers (app/v1/[...path]/route.ts,
 * app/healthz/route.ts, proxy.ts). Same intended contract, entirely different
 * implementation, on the surface that serves production.
 *
 * Nothing in the unit or mocked-e2e suites exercises that surface: they run
 * against a dev server with the API stubbed in the browser, so the proxy is
 * never in the path. This script is the missing gate. It builds the real image,
 * runs it against a stub upstream that echoes what it received, and asserts the
 * behaviours nginx guarantees today.
 *
 * It is deliberately implementation-agnostic — it speaks only HTTP — so the
 * same assertions run unchanged against the Next.js image in Slice 3. That is
 * the point: a contract you can only check on one implementation is not a
 * contract.
 *
 *   node harness/proxy-contract.mjs              build the image, then test
 *   node harness/proxy-contract.mjs --no-build   reuse the existing tag
 *   BASE_URL=http://host:port node harness/proxy-contract.mjs --external
 *                                               test an already-running origin
 *
 * Not part of `frontend-ready`: it needs a Docker daemon and takes minutes.
 * Run it before merging anything that touches the serving layer.
 */
import { spawnSync } from "node:child_process";
import { createServer } from "node:http";

const IMAGE = "ohm-frontend:contract-test";
const CONTAINER = "ohm-frontend-contract-test";
const UPSTREAM_PORT = 8899;
const HOST_PORT = 8899 + 1;

const args = new Set(process.argv.slice(2));
const external = args.has("--external");
const baseUrl = external ? process.env.BASE_URL : `http://127.0.0.1:${HOST_PORT}`;

if (external && !baseUrl) {
  console.error("--external requires BASE_URL");
  process.exit(2);
}

/* ---------------------------------------------------------------- assertions */

const results = [];
function check(name, fn) {
  results.push({ name, fn });
}
function assert(cond, detail) {
  if (!cond) throw new Error(detail);
}

/* ------------------------------------------------------------- stub upstream */

/** Records what the proxy actually forwarded, so headers can be asserted. */
const received = [];

function startUpstream() {
  const server = createServer((req, res) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      received.push({
        method: req.method,
        url: req.url,
        headers: req.headers,
        body: Buffer.concat(chunks).toString("utf-8"),
      });
      // A path the tests use to prove upstream status codes pass through.
      if (req.url.startsWith("/v1/status/")) {
        const code = Number(req.url.split("/v1/status/")[1].split("?")[0]);
        res.writeHead(code, { "content-type": "text/plain", "x-upstream-marker": "yes" });
        res.end(`status ${code}\n`);
        return;
      }
      res.writeHead(200, { "content-type": "application/json", "x-upstream-marker": "yes" });
      res.end(JSON.stringify({ saw: { method: req.method, url: req.url } }));
    });
  });
  return new Promise((resolve) => server.listen(UPSTREAM_PORT, () => resolve(server)));
}

/* ----------------------------------------------------------------- container */

function sh(cmd, cmdArgs, opts = {}) {
  const r = spawnSync(cmd, cmdArgs, { encoding: "utf-8", ...opts });
  return { code: r.status, out: (r.stdout || "") + (r.stderr || "") };
}

function buildImage() {
  process.stdout.write(`→ docker build ${IMAGE} (this takes a few minutes)\n`);
  const r = spawnSync("docker", ["build", "-t", IMAGE, "."], { stdio: "inherit" });
  if (r.status !== 0) {
    console.error("✗ docker build failed");
    process.exit(1);
  }
}

function startContainer() {
  sh("docker", ["rm", "-f", CONTAINER]);
  // host.docker.internal resolves the host from inside the container on Docker
  // Desktop; --add-host keeps it working on plain Linux daemons too.
  const r = sh("docker", [
    "run", "-d", "--name", CONTAINER,
    "--add-host", "host.docker.internal:host-gateway",
    "-e", `API_UPSTREAM_URL=http://host.docker.internal:${UPSTREAM_PORT}`,
    "-e", "PORT=8080",
    "-p", `${HOST_PORT}:8080`,
    IMAGE,
  ]);
  if (r.code !== 0) {
    console.error(`✗ docker run failed:\n${r.out}`);
    process.exit(1);
  }
}

async function waitForReady(url, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${url}/healthz`);
      if (res.ok) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  const logs = sh("docker", ["logs", CONTAINER]);
  throw new Error(`container never became ready.\n${logs.out}`);
}

/* -------------------------------------------------------------- the contract */

check("GET /healthz answers 200 'ok' without touching the backend", async () => {
  const before = received.length;
  const res = await fetch(`${baseUrl}/healthz`);
  assert(res.status === 200, `expected 200, got ${res.status}`);
  assert((await res.text()).trim() === "ok", "body should be 'ok'");
  assert(received.length === before, "healthz must not reach the upstream");
});

check("/v1 prefix is preserved when proxying", async () => {
  const before = received.length;
  await fetch(`${baseUrl}/v1/api/okh`);
  assert(received.length > before, "request never reached the upstream");
  const last = received[received.length - 1];
  assert(last.url === "/v1/api/okh", `upstream saw ${last.url}, expected /v1/api/okh`);
});

check("query strings survive the proxy", async () => {
  await fetch(`${baseUrl}/v1/api/okh?page=2&page_size=100`);
  const last = received[received.length - 1];
  assert(
    last.url === "/v1/api/okh?page=2&page_size=100",
    `upstream saw ${last.url}`,
  );
});

check("forwarding headers are set", async () => {
  await fetch(`${baseUrl}/v1/api/okh`);
  const h = received[received.length - 1].headers;
  assert(h["x-real-ip"], "X-Real-IP missing");
  assert(h["x-forwarded-for"], "X-Forwarded-For missing");
  assert(h["x-forwarded-proto"] === "http", `X-Forwarded-Proto was ${h["x-forwarded-proto"]}`);
});

check("method and body are forwarded intact", async () => {
  await fetch(`${baseUrl}/v1/api/match`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ okh_id: "design-1" }),
  });
  const last = received[received.length - 1];
  assert(last.method === "POST", `method was ${last.method}`);
  assert(last.body === '{"okh_id":"design-1"}', `body was ${last.body}`);
});

check("upstream status codes pass through unchanged", async () => {
  for (const code of [404, 422, 500]) {
    const res = await fetch(`${baseUrl}/v1/status/${code}`);
    assert(res.status === code, `expected ${code}, got ${res.status}`);
    assert(
      res.headers.get("x-upstream-marker") === "yes",
      `response for ${code} did not come from the upstream`,
    );
  }
});

check("a missing /docs page 404s rather than serving the SPA shell", async () => {
  // The regression this exists for: /docs/* once fell through to index.html, so
  // every docs URL returned 200 with the app shell and an undeployed docs site
  // looked healthy to browsers and monitors alike.
  const res = await fetch(`${baseUrl}/docs/definitely-not-a-page`);
  assert(res.status === 404, `expected 404, got ${res.status}`);
});

check("bare /docs redirects to /docs/", async () => {
  const res = await fetch(`${baseUrl}/docs`, { redirect: "manual" });
  assert(res.status === 301, `expected 301, got ${res.status}`);
  const loc = res.headers.get("location");
  assert(loc && loc.endsWith("/docs/"), `Location was ${loc}`);
});

check("unknown app routes fall through to the SPA entry point", async () => {
  const res = await fetch(`${baseUrl}/match`);
  assert(res.status === 200, `expected 200, got ${res.status}`);
  assert(
    (res.headers.get("content-type") || "").includes("text/html"),
    "expected an HTML document",
  );
});

check("build-info.json identifies the image", async () => {
  const res = await fetch(`${baseUrl}/build-info.json`);
  assert(res.status === 200, `expected 200, got ${res.status}`);
  const body = await res.json();
  assert("build" in body, `expected a "build" key, got ${JSON.stringify(body)}`);
});

/* ---------------------------------------------------------------------- main */

async function main() {
  const upstream = await startUpstream();
  let started = false;
  try {
    if (!external) {
      if (!args.has("--no-build")) buildImage();
      startContainer();
      started = true;
      await waitForReady(baseUrl);
    }

    let failed = 0;
    for (const { name, fn } of results) {
      try {
        await fn();
        process.stdout.write(`  ✓ ${name}\n`);
      } catch (err) {
        failed += 1;
        process.stdout.write(`  ✗ ${name}\n      ${err.message}\n`);
      }
    }
    process.stdout.write(
      failed === 0
        ? `\n✓ proxy contract: ${results.length} checks passed\n`
        : `\n✗ proxy contract: ${failed} of ${results.length} checks failed\n`,
    );
    process.exitCode = failed === 0 ? 0 : 1;
  } finally {
    upstream.close();
    if (started) sh("docker", ["rm", "-f", CONTAINER]);
  }
}

main().catch((err) => {
  console.error(err);
  sh("docker", ["rm", "-f", CONTAINER]);
  process.exit(1);
});

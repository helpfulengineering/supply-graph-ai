/**
 * Same-origin `/v1/*` proxy to the OHM API, replacing both the nginx
 * `location /v1/` block (production) and the Vite dev proxy (development).
 * One data path, one failure path: dev and prod requests traverse the same
 * code, and CORS never enters the picture.
 *
 * The upstream is resolved per-request from the environment —
 * `API_UPSTREAM_URL` in containers (unchanged from the nginx contract),
 * `OHM_API_BASE_URL` for local dev — so the built image stays runtime-
 * configurable exactly as envsubst kept nginx.
 */

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
]);

function upstreamBase(): string {
  const url = process.env.API_UPSTREAM_URL || process.env.OHM_API_BASE_URL;
  if (!url) {
    // nginx failed loudly at startup on an unset upstream; the entry script
    // preserves that for containers. In dev, default to the local API.
    return "http://localhost:8001";
  }
  return url.replace(/\/+$/, "");
}

async function proxy(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const target = `${upstreamBase()}${url.pathname}${url.search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  const clientIp = request.headers
    .get("x-forwarded-for")
    ?.split(",")[0]
    ?.trim();
  if (clientIp) headers.set("x-real-ip", clientIp);
  headers.set("x-forwarded-proto", url.protocol.replace(":", ""));

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.body,
      redirect: "manual",
      // Streaming request bodies require half-duplex; harmless for the rest.
      // @ts-expect-error duplex is not in the fetch types yet
      duplex: "half",
      signal: AbortSignal.timeout(120_000), // proxy_read_timeout 120s
    });
  } catch {
    return new Response("Upstream unavailable\n", {
      status: 502,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) responseHeaders.set(key, value);
  });

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const HEAD = proxy;
export const OPTIONS = proxy;

export const dynamic = "force-dynamic";

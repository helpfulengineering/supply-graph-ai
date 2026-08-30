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

function upstreamBase(): string | null {
  const url = process.env.API_UPSTREAM_URL || process.env.OHM_API_BASE_URL;
  if (url) return url.replace(/\/+$/, "");

  // Localhost is a reasonable guess for a developer and a wrong one anywhere
  // else. nginx failed loudly at startup on an unset upstream and entry.sh
  // preserves that for our container — but a platform that runs `next start`
  // directly (Vercel, and anything else without our entrypoint) never sees
  // that check, so the fallback silently produced 502s that read as "the API
  // is down" when the real fault was missing configuration.
  if (process.env.NODE_ENV !== "production") return "http://localhost:8001";
  return null;
}

async function proxy(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const base = upstreamBase();
  if (!base) {
    // Distinguished from "unreachable" on purpose: an operator reading a log
    // needs to know which of the two it is.
    return new Response(
      "API upstream is not configured. Set API_UPSTREAM_URL to the OHM API " +
        "origin (scheme + host, no /v1 path) for this deployment.\n",
      { status: 502, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }
  // Self-reference guard. Pointing API_UPSTREAM_URL at this deployment's own
  // origin makes /v1/* proxy to itself: the platform answers 508 INFINITE_LOOP
  // after burning an invocation per hop, and the message names neither the
  // variable nor the value. Cheap to detect, so detect it.
  const forwardedHost =
    request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (forwardedHost) {
    let upstreamHost: string;
    try {
      upstreamHost = new URL(base).host;
    } catch {
      return new Response(
        `API upstream is not a valid URL: ${base}\nSet API_UPSTREAM_URL to the ` +
          "OHM API origin (scheme + host, no /v1 path).\n",
        { status: 502, headers: { "content-type": "text/plain; charset=utf-8" } },
      );
    }
    if (upstreamHost === forwardedHost) {
      return new Response(
        `API upstream points at this deployment (${forwardedHost}), so /v1 ` +
          "would proxy to itself.\nSet API_UPSTREAM_URL to the OHM API origin, " +
          "not the frontend's own URL.\n",
        { status: 502, headers: { "content-type": "text/plain; charset=utf-8" } },
      );
    }
  }

  const target = `${base}${url.pathname}${url.search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  // No x-real-ip is set here. It was derived from the FIRST X-Forwarded-For
  // entry, which is the part a caller writes themselves — so it laundered
  // client-supplied data into a header that reads as authoritative. Nothing
  // consumed it, and the API resolves the client from X-Forwarded-For against
  // its own trusted-proxy set (src/config/proxy_trust.py), which is where that
  // decision belongs. X-Forwarded-For itself is forwarded unchanged above.
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

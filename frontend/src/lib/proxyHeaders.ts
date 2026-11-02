/**
 * Copy an upstream response's headers onto the proxied response.
 *
 * `Headers.set` keeps one value per name. A sign-in responds with two
 * Set-Cookie headers (the session and the CSRF cookie). Setting the name
 * keeps only the last, and the browser then has nothing to send back.
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

export function copyUpstreamHeaders(upstream: Headers): Headers {
  const responseHeaders = new Headers();
  upstream.forEach((value, key) => {
    if (key.toLowerCase() === "set-cookie") return;
    if (!HOP_BY_HOP.has(key.toLowerCase())) responseHeaders.set(key, value);
  });
  const cookies =
    typeof upstream.getSetCookie === "function" ? upstream.getSetCookie() : [];
  for (const cookie of cookies) responseHeaders.append("set-cookie", cookie);
  return responseHeaders;
}

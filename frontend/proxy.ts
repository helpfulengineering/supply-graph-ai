import { NextResponse, type NextRequest } from "next/server";
import { siteConfig } from "./src/lib/site/config";

/**
 * Trailing-slash policy, split by surface (Next's global redirect is disabled
 * via `skipTrailingSlashRedirect` because one rule cannot serve both):
 *
 * - `/docs/**` — slashes are preserved. mkdocs emits directory URLs with
 *   relative links; stripping the slash would break every link on the page.
 *   The docs route handler owns `/docs` → `/docs/` and directory-index
 *   resolution.
 * - `/v1/**` — passed through byte-for-byte, as nginx did.
 * - App routes — normalized to no trailing slash, restoring the default
 *   behaviour the SPA's router provided.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // The optional site layer is gated here rather than in the page. Whether it
  // is enabled is a build-time constant (NEXT_PUBLIC_* is inlined), so a
  // page-level notFound() renders the boundary but leaves the response 200 —
  // the page looks right while the status lies, which misleads monitors and
  // crawlers. This runs per request and can answer with a real 404. On the
  // default deployment /operator-tools genuinely does not exist.
  if (!siteConfig.enabled && pathname.startsWith("/operator-tools")) {
    return new NextResponse(null, { status: 404 });
  }

  if (
    pathname === "/docs" ||
    pathname.startsWith("/docs/") ||
    pathname.startsWith("/v1/") ||
    pathname === "/"
  ) {
    return NextResponse.next();
  }

  if (pathname.endsWith("/")) {
    // The proxy runtime requires an absolute Location. request.url reflects
    // the server's own binding, not the caller, so rebuild the origin from
    // forwarded headers (set by any ingress) with the Host header as
    // fallback — the origin the client actually used. (Not nextUrl.clone() —
    // NextURL re-serializes the trailing slash it parsed from the request,
    // redirecting the URL to itself.)
    const proto = request.headers.get("x-forwarded-proto") ?? "http";
    const host =
      request.headers.get("x-forwarded-host") ??
      request.headers.get("host") ??
      request.nextUrl.host;
    const target =
      encodeURI(pathname.replace(/\/+$/, "")) + (request.nextUrl.search || "");
    return NextResponse.redirect(`${proto}://${host}${target}`, 308);
  }

  return NextResponse.next();
}

export const config = {
  // Static assets never carry trailing slashes; skip them for cheapness.
  matcher: ["/((?!_next/|favicon.ico|build-info.json).*)"],
};

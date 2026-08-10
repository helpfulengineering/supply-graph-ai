import { promises as fs } from "node:fs";
import path from "node:path";

/**
 * Serve the static mkdocs tree, replacing nginx's `location /docs/` block.
 *
 * The nginx contract this preserves (see the comment history in the removed
 * deploy/nginx.conf.template): `/docs/*` terminates in a 404 when the file is
 * missing rather than falling through to the app shell — a 200 SPA shell for
 * every docs path once masked an undeployed docs site. Directory requests
 * resolve their `index.html`, and a directory reached without its trailing
 * slash redirects so mkdocs' relative links keep resolving.
 */

const DOCS_ROOT = path.resolve(
  process.env.DOCS_ROOT || path.join(process.cwd(), "docs-dist"),
);

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".map": "application/json",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml",
  ".pdf": "application/pdf",
};

function notFound(): Response {
  return new Response("Not found\n", {
    status: 404,
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}

/**
 * Relative Location, as nginx emitted: the container runs behind an ingress,
 * and an absolute URL would leak the internal host and scheme.
 */
function redirectTo(path: string): Response {
  return new Response(null, { status: 301, headers: { location: path } });
}

async function statOrNull(p: string) {
  try {
    return await fs.stat(p);
  } catch {
    return null;
  }
}

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const pathname = decodeURIComponent(url.pathname);

  // `location = /docs { return 301 /docs/; }`
  if (pathname === "/docs") {
    return redirectTo("/docs/");
  }

  const rel = pathname.replace(/^\/docs\//, "");
  const file = path.normalize(path.join(DOCS_ROOT, rel));
  if (!file.startsWith(DOCS_ROOT)) return notFound();

  let target = file;
  let stat = await statOrNull(target);

  if (stat?.isDirectory()) {
    // Directory reached without a trailing slash: redirect so the page's
    // relative links resolve against the directory, as nginx did.
    if (!pathname.endsWith("/")) {
      return redirectTo(`${encodeURI(pathname)}/`);
    }
    target = path.join(target, "index.html");
    stat = await statOrNull(target);
  }

  if (!stat?.isFile()) return notFound();

  const body = await fs.readFile(target);
  return new Response(new Uint8Array(body), {
    headers: {
      "content-type":
        MIME[path.extname(target).toLowerCase()] ?? "application/octet-stream",
    },
  });
}

export const dynamic = "force-dynamic";

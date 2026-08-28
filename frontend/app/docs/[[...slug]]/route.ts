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
 *
 * That contract assumes the tree is present, which is true for our container
 * (the image copies docs-dist) and false anywhere the docs are not built —
 * a Vercel preview, for instance, which has no mkdocs step. Rather than 404
 * every docs link on such a deployment, an absent tree redirects to the
 * published docs site. The distinction is deliberate: a MISSING TREE is a
 * deployment shape, while a missing FILE inside a present tree is the broken
 * link the 404 exists to surface. Set DOCS_FALLBACK_URL to "" to opt out and
 * get the strict 404 everywhere.
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

/** Where docs live when this deployment does not build them itself. */
const DOCS_FALLBACK =
  process.env.DOCS_FALLBACK_URL ?? "https://www.openhardwaremanager.org/docs/";

let docsTreePresent: boolean | null = null;

async function hasDocsTree(): Promise<boolean> {
  if (docsTreePresent === null) {
    const stat = await statOrNull(path.join(DOCS_ROOT, "index.html"));
    docsTreePresent = Boolean(stat?.isFile());
  }
  return docsTreePresent;
}

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

  // No tree in this deployment: send readers to the published docs instead of
  // 404ing every link. Checked before the trailing-slash redirect so /docs and
  // /docs/ behave the same.
  if (!(await hasDocsTree()) && DOCS_FALLBACK) {
    const rest = pathname.replace(/^\/docs\/?/, "");
    return new Response(null, {
      status: 302,
      headers: { location: DOCS_FALLBACK.replace(/\/+$/, "/") + rest },
    });
  }

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

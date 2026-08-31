/**
 * `openhardwaremanager.org/install.sh` — the memorable form of the installer
 * URL (#383).
 *
 * A route rather than a static file, because the site has no static asset
 * directory to drop one into. It redirects rather than serving the script,
 * which is the point: the bytes come from the release asset, checksummed by
 * the release pipeline, so integrity comes from the release process rather
 * than from a second copy that a frontend rebuild could silently stale.
 *
 * `releases/latest/download/<asset>` is GitHub's stable pointer at the newest
 * release, so publishing a release updates what this serves with no step here.
 *
 * 302 rather than 301: the target moves with every release, and a permanent
 * redirect is exactly the thing a client is entitled to cache forever.
 */

const RELEASE_ASSET =
  process.env.OHM_INSTALLER_URL ||
  "https://github.com/helpfulengineering/supply-graph-ai/releases/latest/download/install.sh";

export function GET(): Response {
  return Response.redirect(RELEASE_ASSET, 302);
}

export const dynamic = "force-dynamic";

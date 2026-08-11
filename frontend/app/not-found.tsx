import Link from "next/link";
import { PageHero } from "../src/components/layout/PageHero";

/**
 * The 404, skinned like every other page.
 *
 * The port left this as a client-side redirect home, preserving the old SPA
 * catch-all. That was right for a phase that promised zero change, but it
 * costs a real status: a redirecting boundary answers 200, so an unknown path
 * — or a route gated off by configuration — looked fine to any crawler,
 * monitor, or test asserting on the response. This is a server component with
 * no redirect, so notFound() and unmatched paths both return a true 404.
 */
export default function NotFound() {
  return (
    <div className="space-y-6">
      <PageHero title="Not found" crumb="404 · no such page" />
      <p className="max-w-prose text-sm text-muted-foreground">
        That address does not match anything on this instance. It may have moved,
        or it may be a capability this instance has not enabled.
      </p>
      <Link
        href="/"
        className="inline-flex min-h-11 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground no-underline transition-colors hover:opacity-90"
      >
        Back to the dashboard
      </Link>
    </div>
  );
}

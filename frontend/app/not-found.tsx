import type { Metadata } from "next";
import Link from "next/link";
import { PageHero } from "@/components/layout/PageHero";
import { NAV_GROUPS } from "@/components/layout/nav";
import { PANEL_MUTED } from "@/components/ui/surface";
import { SECTION_LABEL } from "@/components/ui/typography";
import { cn } from "@/lib/utils";

/**
 * The 404, skinned like every other page.
 *
 * The port left this as a client-side redirect home, preserving the old SPA
 * catch-all. That was right for a phase that promised zero change, but it
 * costs a real status: a redirecting boundary answers 200, so an unknown path
 * — or a route gated off by configuration — looked fine to any crawler,
 * monitor, or test asserting on the response. This is a server component with
 * no redirect, so notFound() and unmatched paths both return a true 404.
 *
 * There is deliberately no `app/loading.tsx` above this. A Suspense boundary
 * at the root would let the response start streaming, and a streamed response
 * has already sent its headers — Next documents that the status is then locked
 * at 200. The loading animation lives inside the provider stack instead, where
 * it costs this page nothing.
 */

export const metadata: Metadata = {
  title: "Not found",
  // Belt and braces alongside the 404 status: this page is prerendered once at
  // /_not-found and served for every unmatched path, so it is exactly the kind
  // of URL a crawler should be told not to keep.
  robots: { index: false, follow: true },
};

/** Reuses the 404 and error pages' one shared spelling for a way out. */
const ACTION =
  "inline-flex min-h-11 items-center rounded-md px-4 text-sm font-medium no-underline transition-colors";

export default function NotFound() {
  return (
    <div className="space-y-6">
      {/* The one hero with no section mark. Every other page resolves its icon
          from the sitemap, and this page is prerendered once at /_not-found and
          then served for any unmatched path — so a resolved icon would appear
          only after hydration, and would claim membership of a section the
          address does not actually belong to. */}
      <PageHero title="Not found" crumb="404 · no such page" icon={null} />
      <p className="max-w-prose text-sm text-muted-foreground">
        That address does not match anything on this instance. It may have
        moved, or it may be a capability this instance has not enabled.
      </p>

      {/*
        The sitemap, not a list of guesses.
        A dead end that only offers "go home" makes the visitor start their
        search over. These rows are read from nav.ts — the same table the menu
        and every page hero read — so this page cannot come to offer a route
        that no longer exists, which is the failure mode of a hand-written list
        of helpful links.

        Explore and Create only: Reference is where /help already is, and this
        page links there in its own sentence below.
      */}
      <nav aria-labelledby="not-found-suggestions" className={PANEL_MUTED}>
        <h2 id="not-found-suggestions" className={SECTION_LABEL}>
          Where you might have been going
        </h2>
        <ul className="mt-2 grid gap-x-6 gap-y-1 sm:grid-cols-2">
          {NAV_GROUPS.filter((group) => group.label !== "Reference").flatMap(
            (group) =>
              group.entries.map((entry) => (
                <li key={entry.href}>
                  <Link
                    href={entry.href}
                    className="flex min-h-11 flex-wrap items-baseline gap-x-2 text-sm text-primary-ink hover:underline"
                  >
                    {entry.name}
                    <span className="text-caption text-muted-foreground">
                      {entry.desc}
                    </span>
                  </Link>
                </li>
              )),
          )}
        </ul>
      </nav>

      <div className="flex flex-wrap items-center gap-2">
        <Link
          href="/"
          className={cn(
            ACTION,
            "bg-primary text-primary-foreground hover:opacity-90",
          )}
        >
          Back to the dashboard
        </Link>
        <Link
          href="/help"
          className={cn(
            ACTION,
            "border border-border bg-background text-foreground hover:bg-muted",
          )}
        >
          See everything on this instance
        </Link>
      </div>
    </div>
  );
}

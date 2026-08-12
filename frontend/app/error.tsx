"use client";

import { useEffect, useTransition } from "react";
import Link from "next/link";
import { PageHero } from "@/components/layout/PageHero";
import { LogoLoader } from "@/components/ui/LogoLoader";
import { PANEL_MUTED } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION } from "@/components/ui/typography";
import { userFacingError } from "@/lib/userMessage";
import { cn } from "@/lib/utils";

/**
 * The shared shape of the two escape routes, matching the 404's.
 *
 * `min-h-11` rather than the Button primitive's `h-8`: these are the only
 * controls on a page someone reached by accident, and the responsive gate
 * holds every control to a 24px target — a dead-end page is the last place to
 * make the way out small.
 */
const ACTION =
  "inline-flex min-h-11 items-center rounded-md px-4 text-sm font-medium no-underline transition-colors";

/**
 * The catch-all: any route whose render throws lands here.
 *
 * Without this file the boundary is Next's own, which in production is a bare
 * black-and-white "Application error: a client-side exception has occurred" on
 * an unstyled document — no header, no way back, and no indication whether the
 * fault was the instance, the network, or the address. One thrown error and a
 * visitor was out of the app entirely.
 *
 * This sits under the root layout, so the header, footer, and the current
 * world are all still there: the app had a problem on one page, which is what
 * happened, rather than the site having ended.
 *
 * It cannot catch everything. An error thrown by the root layout itself — or
 * by the provider stack it mounts — is above this boundary, and
 * `global-error.tsx` is the net under that one.
 */
export default function Error({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  // Next 16 renamed this from `reset`: it re-fetches as well as re-rendering,
  // which is what a person pressing "Try again" means by it.
  retry: () => void;
}) {
  // Retrying re-runs the server render, which is not instant and used to give
  // no sign it had started — the button simply sat there, so the natural next
  // move was to press it again. `startTransition` is what marks that work as
  // pending, and the mark is what says so.
  const [retrying, startRetry] = useTransition();

  useEffect(() => {
    // The console is the only sink this app has — there is no error reporting
    // service wired up, and inventing one here would be a decision this change
    // is not the place to make. Without this the digest is the only trace, and
    // it is not printed anywhere a developer would look.
    console.error("Unhandled error rendering this route:", error);
  }, [error]);

  // Nothing curated the throw that landed here, so the exception's own text is
  // not treated as copy — see `trustErrorMessage`. It still gets shown, below,
  // where a raw message reads as a diagnostic rather than as the explanation.
  const message = userFacingError(error, { trustErrorMessage: false });

  return (
    <div className="space-y-6">
      {/* No section mark, for the reason the 404 gives: this boundary renders
          over any route, so a resolved icon would claim whichever section the
          address belongs to while showing a page that is not that section. */}
      {/*
        The mark, animating, above a page that only ever appears when something
        failed. It is doing no work — nothing here is loading — and that is the
        point: a visitor who has just been dropped out of whatever they were
        doing should see the product still running rather than a bare apology,
        and this is the one element on the page that is unmistakably OHM.
      */}
      <LogoLoader className="h-10 w-10" />
      <PageHero
        title={message.title}
        crumb={[{ label: "error" }, { label: "this page did not load" }]}
        icon={null}
      />

      <p className={cn(BODY_MUTED, "max-w-prose")}>{message.body}</p>

      <div className="flex flex-wrap items-center gap-2">
        {/* Offered unconditionally, unlike in ErrorMessage. A render that threw
            is not a request with a status — `retryable` describes what the API
            said, and here there may have been no API call at all. */}
        <button
          onClick={() => startRetry(() => retry())}
          disabled={retrying}
          className={cn(
            ACTION,
            "bg-primary text-primary-foreground hover:opacity-90",
          )}
        >
          {retrying && <LogoLoader className="mr-2 h-4 w-4" />}
          {retrying ? "Trying again…" : "Try again"}
        </button>
        <Link
          href="/"
          className={cn(
            ACTION,
            "border border-border bg-background text-foreground hover:bg-muted",
          )}
        >
          Back to the dashboard
        </Link>
      </div>

      {/*
        The technical detail, kept apart from the explanation above.

        The digest is the useful half: Next deliberately withholds a server
        error's message from the browser so a stack trace cannot leak into a
        page, and sends this hash instead, which matches a line in the
        instance's own logs. Showing it is the difference between an operator
        finding the failure in one grep and asking the reporter to reproduce it.

        The message is the other half, and only ever appears for a client-side
        throw — a server error's message never reaches here to be printed.
      */}
      {(error.digest || error.message) && (
        <div className={cn(PANEL_MUTED, "space-y-1")}>
          <p className={BODY_MUTED}>
            Quote this if you report the problem — it is what an operator needs
            to find it in the instance&apos;s logs.
          </p>
          {error.digest && (
            <p className="font-mono text-sm text-foreground">{error.digest}</p>
          )}
          {error.message && (
            <p className={cn(CAPTION, "break-words font-mono")}>
              {error.message}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

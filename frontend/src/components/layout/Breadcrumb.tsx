"use client";

import { Fragment } from "react";
import Link from "next/link";
import { CHROME_LINK } from "./chromeLink";
import { cn } from "@/lib/utils";

/** One step in a breadcrumb trail. */
export interface BreadcrumbTerm {
  label: string;
  /**
   * Where the step leads. Omitted on the last one: the page you are already on
   * is not a link to itself, and it is marked `aria-current="page"` instead.
   */
  href?: string;
}

/**
 * The trail above a page title, for anything reached from a list.
 *
 * Four views had written this by hand — the design, facility, and package
 * detail pages, plus the facility form — as a flex `<nav>`, a `›` in a span,
 * and a truncated leaf. They had drifted apart in the ways hand-copied markup
 * does:
 *
 *   - Three of the four `<nav>`s had no accessible name, so a screen reader
 *     listing the page's landmarks found an unlabelled navigation region on
 *     every detail page in the app.
 *   - None marked the leaf `aria-current="page"`.
 *   - The trail was 14px on the detail pages and 12px in the hero, so the same
 *     line sat at two sizes depending on the route.
 *   - Links were `hover:text-primary-ink` and nothing else: no underline, no
 *     focus ring of their own.
 *
 * `min-h-6` on the link is the target size, and it is required rather than
 * decorative. WCAG 2.5.8 exempts a target rendered inline within text, but this
 * nav is a flex container, which blockifies its children — so a trail link is a
 * standalone target and owes the full 24px. The hand-rolled versions rendered
 * at 20px and 16px. responsive.spec.ts never caught it: it audits a route as
 * soon as `#main` is visible, which on a data-driven detail page is while the
 * loading state is still on screen, so the trail it would have measured had not
 * rendered yet.
 */
export function Breadcrumb({
  trail,
  className,
}: {
  trail: readonly BreadcrumbTerm[];
  className?: string;
}) {
  return (
    <nav
      aria-label="Breadcrumb"
      className={cn(
        "flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground",
        className,
      )}
    >
      {trail.map((term, i) => (
        <Fragment key={`${term.label}-${i}`}>
          {i > 0 && <span aria-hidden="true">›</span>}
          {term.href ? (
            <Link
              href={term.href}
              className={cn(
                "inline-flex min-h-6 shrink-0 items-center",
                CHROME_LINK,
              )}
            >
              {term.label}
            </Link>
          ) : (
            // The leaf names the current page. Truncated rather than wrapped —
            // a facility name can be longer than a phone is wide, and the trail
            // is one line above a heading that already says the whole thing.
            <span
              aria-current="page"
              className="min-w-0 truncate text-foreground"
            >
              {term.label}
            </span>
          )}
        </Fragment>
      ))}
    </nav>
  );
}

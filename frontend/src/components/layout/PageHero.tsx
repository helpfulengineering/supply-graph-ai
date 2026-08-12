"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import type { NavIcon } from "./nav";
import { navEntryFor } from "./nav";
import { CAPTION, PAGE_TITLE } from "../ui/typography";
import { cn } from "@/lib/utils";

interface PageHeroProps {
  title: ReactNode;
  /**
   * Mono role line beside the title — the admin page's "telemetry · visitors"
   * idiom. A node rather than a string so the terms can be links, as the
   * dashboard's are; it renders inside one inline span, which is what keeps
   * links in it inline text rather than standalone targets.
   */
  crumb?: ReactNode;
  /** Trail above the title, for pages reached from a list. */
  breadcrumb?: ReactNode;
  /** One line under the rule. Keep it to what the page is for. */
  description?: ReactNode;
  actions?: ReactNode;
  /**
   * Override the icon resolved from the route. `null` suppresses it — for
   * pages with no place in the sitemap, where an invented icon would imply a
   * section that does not exist.
   */
  icon?: NavIcon | null;
  /** Token utility for the icon's colour; defaults to the route's group accent. */
  accent?: string;
}

/**
 * The page hero, matched to ohm.thetechmargin.com/admin: a concise baseline
 * row — the section mark, the h1 at heading scale, a mono crumb — closed by
 * the iridescent rule. The site bar above stays pure chrome; this is where a
 * page states its identity, so the brand rule lives here.
 *
 * The icon is not a prop each page picks. It is resolved from the current
 * route through the sitemap (nav.ts), so the glyph beside an h1 is by
 * construction the glyph next to that route in the menu — including on detail
 * pages, which inherit the icon of the list they belong to. Choosing per page
 * is what lets a menu and a page drift into looking like two products; the
 * only decisions left are the deliberate ones, `icon` and `accent`.
 *
 * Breadcrumb and description are part of the hero rather than each page's
 * own markup. Six pages had hand-rolled versions with their own spacing, so
 * the same three elements sat at three different rhythms depending on which
 * route you were on. One component, one rhythm.
 *
 * The rule is static: an animated shimmer would leave a permanently-running
 * animation, and the axe helper waits for animations to settle before every
 * scan — each of the 20 theme-matrix scans would eat the full timeout.
 */
export function PageHero({
  title,
  crumb,
  breadcrumb,
  description,
  actions,
  icon,
  accent,
}: PageHeroProps) {
  const resolved = navEntryFor(usePathname() ?? "");
  // `undefined` means "resolve from the route"; `null` means "no icon".
  const Icon: NavIcon | null =
    icon === undefined ? (resolved?.entry.icon ?? null) : icon;
  const tone = accent ?? resolved?.group.accent ?? "text-muted-foreground";

  return (
    <header className="mb-3">
      {breadcrumb && (
        <nav
          aria-label="Breadcrumb"
          className="mb-1 flex items-center gap-1.5 text-xs text-muted-foreground"
        >
          {breadcrumb}
        </nav>
      )}
      <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
        {Icon && (
          // Decorative: the h1 beside it already says which page this is, and
          // a screen reader announcing "wrench, Designs" adds a word, not a
          // fact. Centred rather than baseline-aligned — a glyph has no
          // baseline of its own, and sitting it on the text's would hang it
          // below the cap height it is meant to match.
          <Icon
            aria-hidden="true"
            className={`h-5 w-5 shrink-0 self-center ${tone}`}
          />
        )}
        <h1 className={PAGE_TITLE}>{title}</h1>
        {crumb && <span className={cn(CAPTION, "font-mono")}>{crumb}</span>}
        {actions && (
          <span className="ml-auto flex items-center gap-2">{actions}</span>
        )}
      </div>
      <div
        aria-hidden="true"
        className="mt-1.5 h-px w-full rounded-full"
        style={{
          background:
            "linear-gradient(120deg, var(--ttm-irid-a), var(--ttm-irid-b), var(--ttm-irid-c), var(--ttm-irid-d), var(--ttm-irid-e))",
        }}
      />
      {description && (
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      )}
    </header>
  );
}

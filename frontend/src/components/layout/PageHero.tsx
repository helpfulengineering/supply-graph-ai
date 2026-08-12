"use client";

import { Fragment, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavIcon } from "./nav";
import { navEntryFor } from "./nav";
import { CAPTION, PAGE_TITLE } from "../ui/typography";
import { cn } from "@/lib/utils";

/** One term in a hero crumb. */
export interface CrumbTerm {
  label: string;
  /**
   * Where the term leads.
   *
   * Omitted when the term names an aspect of the page rather than a place —
   * "facets", "versions", "federated" are descriptions, and linking them
   * somewhere approximate is worse than leaving them as text.
   *
   * Also omitted when the page already carries that navigation: Settings names
   * "session · keys · identities" over a tab bar of exactly those, and linking
   * the crumb there put two links to the same href under the same name on one
   * page — a duplicate control for a pointer, a second identical stop for a
   * screen reader. A crumb links where it is the only way to somewhere.
   */
  href?: string;
}

/** Between terms. A text node, deliberately — see CrumbTerms. */
const CRUMB_SEPARATOR = " · ";

/**
 * The one place a crumb link is styled.
 *
 * A dotted underline at rest rather than a colour change on hover: a crumb is
 * one muted line, so a link that only announces itself under a cursor is
 * invisible to anyone arriving by keyboard, and "hover to discover" is not an
 * affordance on a touch screen.
 *
 * The `!` is load-bearing. index.css carries an unlayered
 * `a { text-decoration: none }`, and Tailwind v4 puts utilities in a cascade
 * layer — unlayered rules beat layered ones whatever their specificity, so a
 * plain `underline` class on an anchor computes to text-decoration-line: none.
 * The same is true of the other underline utilities on links in this app, which
 * is a fix for the reset's layer rather than for one component.
 */
const CRUMB_LINK =
  "rounded-sm underline! decoration-dotted! underline-offset-4 hover:text-foreground hover:decoration-solid! focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/**
 * The terms of a crumb, linked where they lead somewhere.
 *
 * Separators are emitted as text nodes beside the links rather than as wrappers
 * around them, and the whole crumb stays inside PageHero's single inline span.
 * That is what keeps these inline text under WCAG 2.5.8's inline exception,
 * which responsive.spec.ts implements literally: it exempts an inline element
 * whose parent is neither flex nor grid and carries text besides the link
 * itself. A term is roughly 19px tall, so giving each its own flex row would
 * turn all of them into standalone targets required to reach 24px — which
 * caption scale cannot do without breaking the line box.
 */
function CrumbTerms({
  terms,
  pathname,
}: {
  terms: readonly CrumbTerm[];
  pathname: string;
}) {
  return terms.map((term, i) => (
    <Fragment key={term.label}>
      {i > 0 && CRUMB_SEPARATOR}
      {term.href ? (
        <Link
          href={term.href}
          // A crumb names siblings, so one of them is often the page you are
          // already on — "session" while on /settings/session. Marked rather
          // than removed: the term still belongs in the line, and a screen
          // reader should be told which one is the current page instead of
          // being offered three destinations that look alike.
          aria-current={term.href === pathname ? "page" : undefined}
          className={CRUMB_LINK}
        >
          {term.label}
        </Link>
      ) : (
        term.label
      )}
    </Fragment>
  ));
}

interface PageHeroProps {
  title: ReactNode;
  /**
   * Mono role line beside the title — the admin page's "telemetry · visitors"
   * idiom. Terms rather than a sentence, so any of them that names a
   * destination is a link without each view rebuilding the markup; a plain
   * string still renders as it always did.
   */
  crumb?: string | readonly CrumbTerm[];
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
  const pathname = usePathname() ?? "";
  const resolved = navEntryFor(pathname);
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
        {crumb && (
          // data-crumb marks the role line for the cross-view gate in
          // crumb.spec.ts. The hero's other slots hold links too — the
          // breadcrumb above it, and `actions` beside it — so a spec looking
          // for "links in the hero" would measure those and pass while a crumb
          // stayed unreachable.
          <span data-crumb="" className={cn(CAPTION, "font-mono")}>
            {typeof crumb === "string" ? (
              crumb
            ) : (
              <CrumbTerms terms={crumb} pathname={pathname} />
            )}
          </span>
        )}
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

import {
  EfficiencyIcon,
  HelpIcon,
  CubeIcon,
  NotebookIcon,
  BobbinIcon,
  LiquidIcon,
  OwlIcon,
  IndustrialProductionIcon,
  IntegrationIcon,
  PackingIcon,
  RobotIcon,
  SettingsIcon,
  ShowcaseIcon,
  SmartFactoryIcon,
  ArtificialLeavesIcon,
  type IconProps,
} from "../icons";
import type { JSX } from "react";

/**
 * The sitemap — single source for everything that names a route.
 *
 * Every navigable route is here, grouped by purpose, each entry carrying a
 * role line and an icon rather than a bare label. Adding a page means adding
 * one row; the chrome asks nothing else, and e2e/chrome.spec.ts walks this
 * list so a missing entry fails CI.
 *
 * "Everything" now means the drawer, the Help page's sitemap, AND each page's
 * own hero — PageHero resolves the current route through `navEntryFor` and
 * wears that entry's icon and accent. That is the point: the icon you clicked
 * in the menu is the icon at the top of the page you land on, so the two read
 * as one surface rather than as a menu and an unrelated document. It only
 * holds while this table is the sole source, which is why the drawer's
 * Account and Site rows moved here instead of staying inline in the drawer.
 *
 * Icons come from the purchased general set, drawn at the same 20px the list
 * renders at and checked there rather than assumed. The distinction that
 * matters is which set: the future-technology illustrations carry 200–3000
 * units of path data drawn for 100pt and do collapse at this size — they earn
 * their place at 40px+, which is where the empty states use them
 * (components/ui/illustrations.tsx). The general set is line art and holds.
 */

/**
 * What a nav row draws.
 *
 * Widened from `LucideIcon` when the rows moved to the purchased set: a
 * ForwardRefExoticComponent is not the same shape as a plain function
 * component, and the entries are the latter.
 */
export type NavIcon = (props: IconProps) => JSX.Element;

export interface NavEntry {
  href: string;
  name: string;
  desc: string;
  icon: NavIcon;
  /**
   * Prefix that counts as "on this page", when it is wider than the link.
   *
   * Settings is the case that needs it: the menu links straight to the session
   * subtab, but every /settings/* subtab is still the Settings page, and
   * neither the active state nor the page's own hero should blink out when you
   * move between them.
   */
  match?: string;
  /** Rendered as <a> not <Link> — targets outside the app router. */
  external?: boolean;
}

/** The prefix an entry claims: its explicit `match`, else its own href. */
export function navEntryPath(entry: NavEntry): string {
  return entry.match ?? entry.href;
}

export interface NavGroup {
  label: string;
  entries: NavEntry[];
  /**
   * Icon colour for this group, as a token utility.
   *
   * Grouping by hue gives the drawer a second, pre-verbal cue: browse surfaces
   * read one way, authoring another. These are chart tokens, not new colours —
   * they are the categorical ramp the theme layer already proves distinct in
   * all twenty variants, so the drawer re-themes with everything else and adds
   * nothing for the contrast gate to check.
   */
  accent: string;
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Explore",
    accent: "text-chart-1",
    entries: [
      {
        href: "/",
        name: "Dashboard",
        desc: "network map and system status",
        icon: OwlIcon,
      },
      {
        href: "/okh",
        name: "Designs",
        desc: "browse the open hardware catalog",
        icon: CubeIcon,
      },
      {
        href: "/facilities",
        name: "Facilities",
        desc: "manufacturing spaces, local and federated",
        icon: SmartFactoryIcon,
      },
      {
        href: "/packages",
        name: "Packages",
        desc: "versioned design bundles",
        icon: PackingIcon,
      },
      // Shares ArtificialLeavesIcon with the Supply Tree entry below: this is
      // the browse for those results, and the two cannot inherit from each
      // other the way a detail route inherits from its list (navEntryFor
      // matches on prefix, and /visualization/:id is not under /solutions).
      // Same glyph is what keeps them reading as one section anyway.
      {
        href: "/solutions",
        name: "Solutions",
        desc: "supply trees saved from your matches",
        icon: ArtificialLeavesIcon,
      },
    ],
  },
  {
    label: "Create",
    accent: "text-chart-2",
    entries: [
      {
        href: "/match",
        name: "Match",
        desc: "pair a design with facilities that can build it",
        icon: IntegrationIcon,
      },
      {
        href: "/okh/generate",
        name: "Generate",
        desc: "draft a design manifest from a URL",
        icon: RobotIcon,
      },
      {
        href: "/okh/new",
        name: "New design",
        desc: "author an OKH manifest by hand",
        icon: LiquidIcon,
      },
      {
        href: "/facilities/new",
        name: "New facility",
        desc: "register an OKW space",
        icon: IndustrialProductionIcon,
      },
      {
        href: "/rfq",
        name: "RFQ",
        desc: "request quotes for a matched solution",
        icon: BobbinIcon,
      },
    ],
  },
  {
    label: "Reference",
    accent: "text-chart-3",
    entries: [
      {
        href: "/help",
        name: "Help",
        desc: "sitemap, shortcuts, and accessibility",
        icon: HelpIcon,
      },
      // Static mkdocs site served on the same origin — a hard link, not a route.
      {
        href: "/docs/",
        name: "Documentation",
        desc: "guides and API reference",
        icon: NotebookIcon,
        external: true,
      },
      // Reference rather than Operator: the gallery documents the icon set this
      // interface is drawn from, which is the same kind of thing as the docs
      // beside it. It was in no group at all, so navEntryFor("/icons") returned
      // undefined and the one page whose subject is icons rendered without one.
      {
        href: "/icons",
        name: "Icons",
        desc: "the glyph set, drawn at the sizes it ships at",
        icon: ShowcaseIcon,
      },
    ],
  },
];
// Deliberately absent from NAV_GROUPS: bare /visualization is a redirect, now
// to /solutions — the browse it lacked when it redirected home. Detail routes
// (/okh/[id], /facilities/[id], /packages/[org]/[project]/[version],
// /okh/[id]/files/*) are reached from their lists, and /settings/* subtabs
// from the Settings page's own tab strip.
//
// tests/parity guards only the top-level segment set, not the route set —
// /okh/generate and /settings/reputation both collapse to an existing segment
// and would raise nothing. Menu membership is guarded by e2e/chrome.spec.ts
// and chord coverage by shortcuts.test.ts, which are the checks that actually
// fail when a row is missing.

/**
 * The account entry, in the sitemap rather than inline in the drawer.
 *
 * Its label is the one thing the drawer still decides for itself — Connect /
 * Session / Settings depending on whether you hold an API key — but the
 * route, the icon, and the accent belong here with every other destination,
 * so Help and the page hero read the same row the drawer does.
 */
export const ACCOUNT_GROUP: NavGroup = {
  label: "Account",
  accent: "text-chart-4",
  entries: [
    {
      href: "/settings/session",
      match: "/settings",
      name: "Settings",
      desc: "your API session, and instance administration when your key allows it",
      icon: SettingsIcon,
    },
  ],
};

/**
 * The operator surface, which most instances do not run.
 *
 * Absent from the drawer entirely unless the instance opted in — see
 * NavDrawer — but its icon still has to resolve, because a page that IS
 * mounted needs a hero. The gate is the site layer's configuration, not a
 * preference: without it the page has no data source, so an always-visible
 * entry would lead somewhere that cannot work.
 *
 * Labelled "Operator" rather than "Site": the group is what an operator does
 * with the instance — telemetry, visitor records, administration — and "Site"
 * read as a place rather than a role.
 */
export const SITE_GROUP: NavGroup = {
  label: "Operator",
  accent: "text-chart-5",
  entries: [
    {
      href: "/operator-tools",
      name: "Operator Tools",
      desc: "telemetry, visitor records, and instance administration",
      icon: EfficiencyIcon,
    },
  ],
};

/**
 * Routes that have a page but no menu entry, so their heroes still resolve.
 *
 * A supply tree is a match result rather than a browsable collection, which
 * is why it is not in the drawer — but it is a real page with a real
 * identity, and leaving it iconless would make it the one surface where the
 * connection between menu and page visibly breaks.
 */
export const UNLISTED_GROUP: NavGroup = {
  label: "Results",
  // Explore's accent, not its own: a supply tree is the detail view of the
  // Solutions row, and giving the pair one hue keeps the list and the thing it
  // opens from reading as two unrelated sections.
  accent: "text-chart-1",
  entries: [
    {
      href: "/visualization",
      name: "Supply Tree",
      desc: "the production plan a match resolved to",
      icon: ArtificialLeavesIcon,
    },
  ],
};

/** Every group that carries a resolvable route, menu-visible or not. */
export const ALL_GROUPS: NavGroup[] = [
  ...NAV_GROUPS,
  ACCOUNT_GROUP,
  SITE_GROUP,
  UNLISTED_GROUP,
];

/** Matches the old NavLink prefix behaviour (no `end` prop). */
export function isActivePath(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export interface ResolvedNavEntry {
  entry: NavEntry;
  group: NavGroup;
}

/**
 * The sitemap row a pathname belongs to, or undefined outside the app.
 *
 * Longest match wins, which is what makes detail and sub-routes work: /okh/new
 * is its own entry and must not resolve to /okh, while /okh/okh-0001 has no
 * entry of its own and should resolve to the catalog it was reached from. A
 * shortest-first scan gets both of those backwards.
 *
 * "/" is excluded from prefix matching by isActivePath, so it wins only on an
 * exact match and does not swallow every route in the app.
 */
export function navEntryFor(pathname: string): ResolvedNavEntry | undefined {
  let best: ResolvedNavEntry | undefined;
  for (const group of ALL_GROUPS) {
    for (const entry of group.entries) {
      const path = navEntryPath(entry);
      if (entry.external || !isActivePath(pathname, path)) continue;
      if (!best || path.length > navEntryPath(best.entry).length) {
        best = { entry, group };
      }
    }
  }
  return best;
}

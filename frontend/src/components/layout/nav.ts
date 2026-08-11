import {
  BookText,
  FactoryIcon,
  FilePlus2,
  FileText,
  LayoutDashboard,
  LifeBuoy,
  MapPinned,
  Package,
  Sparkles,
  Wrench,
  Zap,
  type LucideIcon,
} from "lucide-react";

/**
 * The sitemap — single source for everything the drawer renders.
 *
 * Every navigable route is here, grouped by purpose, each entry carrying a
 * role line and an icon rather than a bare label. Adding a page means adding
 * one row; the chrome asks nothing else, and e2e/chrome.spec.ts walks this
 * list so a missing entry fails CI.
 *
 * Icons are lucide, not the Noun Project illustration set. That is measured,
 * not assumed: the illustrations carry 200–3000 units of path data drawn for
 * 100pt, and at the 20px this list renders they collapse into unreadable
 * blobs. They earn their place at 40px+, which is where the empty states use
 * them (components/ui/illustrations.tsx).
 */

export interface NavEntry {
  href: string;
  name: string;
  desc: string;
  icon: LucideIcon;
  /** Rendered as <a> not <Link> — targets outside the app router. */
  external?: boolean;
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
        icon: LayoutDashboard,
      },
      {
        href: "/okh",
        name: "Designs",
        desc: "browse the open hardware catalog",
        icon: Wrench,
      },
      {
        href: "/facilities",
        name: "Facilities",
        desc: "manufacturing spaces, local and federated",
        icon: MapPinned,
      },
      {
        href: "/packages",
        name: "Packages",
        desc: "versioned design bundles",
        icon: Package,
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
        icon: Zap,
      },
      {
        href: "/okh/generate",
        name: "Generate",
        desc: "draft a design manifest from a URL",
        icon: Sparkles,
      },
      {
        href: "/okh/new",
        name: "New design",
        desc: "author an OKH manifest by hand",
        icon: FilePlus2,
      },
      {
        href: "/facilities/new",
        name: "New facility",
        desc: "register an OKW space",
        icon: FactoryIcon,
      },
      {
        href: "/rfq",
        name: "RFQ",
        desc: "request quotes for a matched solution",
        icon: FileText,
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
        icon: LifeBuoy,
      },
      // Static mkdocs site served on the same origin — a hard link, not a route.
      {
        href: "/docs/",
        name: "Documentation",
        desc: "guides and API reference",
        icon: BookText,
        external: true,
      },
    ],
  },
];
// Deliberately absent: /visualization redirects home by design — supply
// trees are per-match results, with no browse list. Detail routes
// (/okh/[id], /facilities/[id], /packages/[org]/[project]/[version],
// /okh/[id]/files/*) are reached from their lists, and /settings/* subtabs
// from the Settings page's own tab strip. tests/parity guards the set.

/** Matches the old NavLink prefix behaviour (no `end` prop). */
export function isActivePath(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

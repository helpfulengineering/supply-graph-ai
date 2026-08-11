/**
 * The sitemap — single source for everything the drawer renders.
 *
 * Every route in the app is reachable from here, grouped by purpose, each
 * entry carrying a role line rather than a bare label. Adding a page means
 * adding one row; the chrome asks nothing else.
 */

export interface NavEntry {
  href: string;
  name: string;
  desc: string;
  /** Rendered as <a> not <Link> — targets outside the app router. */
  external?: boolean;
}

export interface NavGroup {
  label: string;
  entries: NavEntry[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Explore",
    entries: [
      { href: "/", name: "Dashboard", desc: "network map and system status" },
      { href: "/okh", name: "Designs", desc: "browse the open hardware catalog" },
      { href: "/facilities", name: "Facilities", desc: "manufacturing spaces, local and federated" },
      { href: "/packages", name: "Packages", desc: "versioned design bundles" },
    ],
  },
  {
    label: "Create",
    entries: [
      { href: "/match", name: "Match", desc: "pair a design with facilities that can build it" },
      { href: "/okh/generate", name: "Generate", desc: "draft a design manifest from a URL" },
      { href: "/okh/new", name: "New design", desc: "author an OKH manifest by hand" },
      { href: "/facilities/new", name: "New facility", desc: "register an OKW space" },
      { href: "/rfq", name: "RFQ", desc: "request quotes for a matched solution" },
    ],
  },
  // Deliberately absent: /visualization redirects home by design — supply
  // trees are per-match results reached from their match, with no browse list.
  // Every other route in app/ is attached here; tests/parity guards the set.
  {
    label: "Reference",
    entries: [
      // Static mkdocs site served on the same origin — a hard link, not a route.
      { href: "/docs/", name: "Documentation", desc: "guides and API reference", external: true },
    ],
  },
];

/** Matches the old NavLink prefix behaviour (no `end` prop). */
export function isActivePath(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

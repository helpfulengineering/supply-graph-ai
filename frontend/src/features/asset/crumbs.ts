/**
 * Hero crumbs for the asset section.
 *
 * Hoisted rather than written inline because two of them are used on more than
 * one surface, and because the reason a term does NOT link belongs next to the
 * term — which is the whole point of the one-crumb-shape convention: the
 * absence of an href is something an author wrote, and this is where they
 * wrote it.
 */
import type { CrumbTerm } from "@/components/layout/PageHero";

export const ASSET_CRUMB: readonly CrumbTerm[] = [
  { label: "fleet", href: "/assets" },
  // Aspect, not a place. Triage happens per asset, at /assets/{id}/triage —
  // there are as many of those as there are units and no index over them, so
  // linking this would mean picking one arbitrarily.
  { label: "triage" },
  { label: "salvage", href: "/assets/salvage" },
  { label: "designs", href: "/okh" },
];

export const SALVAGE_CRUMB: readonly CrumbTerm[] = [
  { label: "fleet", href: "/assets" },
  // Aspect: names the filter this page applies (harvestable components), not
  // somewhere to go.
  { label: "harvestable" },
  { label: "designs", href: "/okh" },
];

/**
 * The detail page's crumb links all three of its terms, because the page has
 * no tab strip and these anchors are the only navigation to those sections —
 * which is exactly the condition PageHero names for a term linking.
 */
export const ASSET_DETAIL_CRUMB: readonly CrumbTerm[] = [
  { label: "components", href: "#components" },
  { label: "triage report", href: "#triage-report" },
  { label: "sourcing", href: "#sourcing" },
];

export function triageCrumb(manifestId: string): readonly CrumbTerm[] {
  return [
    // Aspect: this page IS the checklist. A link would point at itself under a
    // second name.
    { label: "checklist" },
    { label: "design", href: `/okh/${manifestId}` },
  ];
}

export const NEW_ASSET_CRUMB: readonly CrumbTerm[] = [
  // Aspect: what is being registered, not a place.
  { label: "unit" },
  { label: "designs", href: "/okh" },
];

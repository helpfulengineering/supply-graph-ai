/** Browser-local OHM matching domain preference (Settings → Domain). */

export type OhmDomain = "manufacturing" | "cooking";

export const DEFAULT_DOMAIN: OhmDomain = "manufacturing";

export const STORAGE_KEY = "ohm-domain";

export interface DomainNavItem {
  to: string;
  label: string;
  icon: string;
}

const MANUFACTURING_NAV: DomainNavItem[] = [
  { to: "/okh", label: "Designs", icon: "🔩" },
  { to: "/facilities", label: "Facilities", icon: "🏭" },
  { to: "/packages", label: "Packages", icon: "📦" },
  { to: "/match", label: "Match", icon: "⚡" },
];

const COOKING_NAV: DomainNavItem[] = [
  { to: "/okh", label: "Recipes", icon: "🍳" },
  { to: "/facilities", label: "Kitchens", icon: "🍽️" },
];

/** Coerce a stored/API value to a known domain; unknown → manufacturing. */
export function parseDomain(raw: string | null | undefined): OhmDomain {
  if (raw === "cooking" || raw === "manufacturing") return raw;
  return DEFAULT_DOMAIN;
}

/** Primary nav items for the selected domain (Settings/Docs are separate). */
export function navItemsForDomain(domain: OhmDomain): DomainNavItem[] {
  return domain === "cooking" ? COOKING_NAV : MANUFACTURING_NAV;
}

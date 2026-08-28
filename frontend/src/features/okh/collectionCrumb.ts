import type { CrumbTerm } from "@/components/layout/PageHero";

/**
 * All three link, and all three are anchors.
 *
 * The page has no tab strip, and export / compare / import are the three
 * things it does in the order it does them — which is exactly when PageHero
 * says a term should lead somewhere.
 */
export const COLLECTION_CRUMB: readonly CrumbTerm[] = [
  { label: "export", href: "#export" },
  { label: "compare", href: "#compare" },
  { label: "import", href: "#import" },
];

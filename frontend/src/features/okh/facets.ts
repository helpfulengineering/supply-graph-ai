import type { OkhManifest } from "../../types/okh";
import { deriveCategories } from "./categories";
import { normalizeHardwareLicense } from "./normalizeHardwareLicense";

/**
 * Faceted-browse logic for the OKH catalog (pure, framework-free, unit-tested).
 *
 * `category` is the primary drill-down facet (provisional, derived from the
 * manifest `function`/title/keywords — see categories.ts; swaps to the
 * service-backed taxonomy in Epic #199). The rest are orthogonal facets derived
 * from fields populated across the real corpus: manufacturing process and
 * hardware license. (keywords / development_stage dropped — sparse / no variance;
 * material dropped — generate-from-url emits noisy non-material artifacts that
 * make it useless as a filter until the pipeline's output quality is fixed.)
 */

export type FacetKey = "category" | "process" | "license";

/** The primary drill-down facet, rendered first and marked provisional. */
export const PRIMARY_FACET: FacetKey = "category";

export interface FacetDef {
  key: FacetKey;
  label: string;
  /** All facet values a manifest contributes to this group (0..n). */
  values: (item: OkhManifest) => string[];
}

export const FACET_DEFS: FacetDef[] = [
  {
    key: "category",
    label: "Category",
    values: (i) => deriveCategories(i),
  },
  {
    key: "process",
    label: "Manufacturing process",
    values: (i) => i.manufacturing_processes ?? [],
  },
  {
    key: "license",
    label: "License",
    values: (i) => {
      const n = normalizeHardwareLicense(i.license?.hardware);
      return n ? [n] : [];
    },
  },
];

export type FacetSelections = Partial<Record<FacetKey, string[]>>;

export interface FacetOption {
  value: string;
  count: number;
}
export interface FacetGroup {
  key: FacetKey;
  label: string;
  options: FacetOption[];
}

const DEFS_BY_KEY: Record<FacetKey, FacetDef> = Object.fromEntries(
  FACET_DEFS.map((d) => [d.key, d]),
) as Record<FacetKey, FacetDef>;

/** Does an item satisfy the selections in a single group? (OR within a group.) */
function matchesGroup(
  item: OkhManifest,
  key: FacetKey,
  selected: string[],
): boolean {
  if (selected.length === 0) return true;
  const vals = DEFS_BY_KEY[key].values(item);
  return selected.some((s) => vals.includes(s));
}

/** AND across groups, OR within each group — standard faceted filtering. */
export function matchesSelections(
  item: OkhManifest,
  selections: FacetSelections,
): boolean {
  return FACET_DEFS.every((d) =>
    matchesGroup(item, d.key, selections[d.key] ?? []),
  );
}

export function filterItems(
  items: OkhManifest[],
  selections: FacetSelections,
): OkhManifest[] {
  return items.filter((i) => matchesSelections(i, selections));
}

/**
 * Build facet groups with option counts. Each group's counts reflect the items
 * that pass every *other* group's selections (drill-down counts), so counts
 * preview what selecting an option would yield.
 */
export function deriveFacetGroups(
  items: OkhManifest[],
  selections: FacetSelections,
): FacetGroup[] {
  return FACET_DEFS.map((def) => {
    const otherSelections: FacetSelections = { ...selections, [def.key]: [] };
    const scoped = items.filter((i) => matchesSelections(i, otherSelections));
    const counts = new Map<string, number>();
    for (const item of scoped) {
      for (const v of def.values(item)) {
        counts.set(v, (counts.get(v) ?? 0) + 1);
      }
    }
    const options = [...counts.entries()]
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) =>
        // Licenses: alphabetical (family names are easier to scan than by count).
        // Other facets: count desc, then alpha for ties.
        def.key === "license"
          ? a.value.localeCompare(b.value)
          : b.count - a.count || a.value.localeCompare(b.value),
      );
    return { key: def.key, label: def.label, options };
  }).filter((g) => g.options.length > 0);
}

export function countSelected(selections: FacetSelections): number {
  return FACET_DEFS.reduce(
    (n, d) => n + (selections[d.key]?.length ?? 0),
    0,
  );
}

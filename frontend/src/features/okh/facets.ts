import type { OkhManifest } from "../../types/okh";

/**
 * Faceted-browse logic for the OKH catalog (pure, framework-free, unit-tested).
 *
 * Facets are derived from fields that are actually populated across the real
 * manifest corpus: manufacturing process, hardware license, and material.
 * (keywords and development_stage were dropped — too sparse / no variance.)
 */

export type FacetKey = "process" | "license" | "material";

export interface FacetDef {
  key: FacetKey;
  label: string;
  /** All facet values a manifest contributes to this group (0..n). */
  values: (item: OkhManifest) => string[];
}

export const FACET_DEFS: FacetDef[] = [
  {
    key: "process",
    label: "Manufacturing process",
    values: (i) => i.manufacturing_processes ?? [],
  },
  {
    key: "license",
    label: "License",
    values: (i) => (i.license?.hardware ? [i.license.hardware] : []),
  },
  {
    key: "material",
    label: "Material",
    values: (i) =>
      (i.materials ?? []).map((m) => m.name).filter((n): n is string => !!n),
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
      .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
    return { key: def.key, label: def.label, options };
  }).filter((g) => g.options.length > 0);
}

export function countSelected(selections: FacetSelections): number {
  return FACET_DEFS.reduce(
    (n, d) => n + (selections[d.key]?.length ?? 0),
    0,
  );
}

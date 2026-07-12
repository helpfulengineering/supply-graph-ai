import type { OkhManifest } from "../../types/okh";
import { deriveCategories, UNCATEGORIZED } from "./categories";
import { formatOkhDisplayTitle } from "./formatOkhDisplayTitle";
import { normalizeHardwareLicense } from "./normalizeHardwareLicense";

export type CatalogView = "catalog" | "list";
export type CatalogSort = "alpha" | "category";
export type CatalogGroupBy = "none" | "category" | "process" | "license";

export interface CatalogGroup {
  label: string;
  items: OkhManifest[];
}

export function primaryCategory(item: OkhManifest): string {
  return deriveCategories(item)[0] ?? UNCATEGORIZED;
}

export function primaryProcess(item: OkhManifest): string {
  const p = item.manufacturing_processes?.[0]?.trim();
  return p || "Unspecified";
}

export function primaryLicense(item: OkhManifest): string {
  return normalizeHardwareLicense(item.license?.hardware) ?? "Unspecified";
}

export function sortOkhItems(
  items: OkhManifest[],
  sort: CatalogSort,
): OkhManifest[] {
  const copy = [...items];
  copy.sort((a, b) => {
    if (sort === "category") {
      const ca = primaryCategory(a);
      const cb = primaryCategory(b);
      const byCat = ca.localeCompare(cb);
      if (byCat !== 0) return byCat;
    }
    return formatOkhDisplayTitle(a.title).localeCompare(
      formatOkhDisplayTitle(b.title),
    );
  });
  return copy;
}

function groupKey(item: OkhManifest, groupBy: CatalogGroupBy): string {
  if (groupBy === "category") return primaryCategory(item);
  if (groupBy === "process") return primaryProcess(item);
  if (groupBy === "license") return primaryLicense(item);
  return "";
}

/** Sort items, then bucket into labeled groups (stable within each group). */
export function groupOkhItems(
  items: OkhManifest[],
  groupBy: CatalogGroupBy,
  sort: CatalogSort,
): CatalogGroup[] {
  const sorted = sortOkhItems(items, sort);
  if (groupBy === "none") {
    return [{ label: "", items: sorted }];
  }

  const buckets = new Map<string, OkhManifest[]>();
  for (const item of sorted) {
    const key = groupKey(item, groupBy);
    const list = buckets.get(key);
    if (list) list.push(item);
    else buckets.set(key, [item]);
  }

  return [...buckets.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([label, groupItems]) => ({ label, items: groupItems }));
}

/** Flatten groups, slice a page, then rebuild contiguous group sections. */
export function paginateGroups(
  groups: CatalogGroup[],
  page: number,
  pageSize: number,
): CatalogGroup[] {
  const flat = groups.flatMap((g) =>
    g.items.map((item) => ({ label: g.label, item })),
  );
  const start = (page - 1) * pageSize;
  const slice = flat.slice(start, start + pageSize);
  const out: CatalogGroup[] = [];
  for (const row of slice) {
    const last = out[out.length - 1];
    if (last && last.label === row.label) {
      last.items.push(row.item);
    } else {
      out.push({ label: row.label, items: [row.item] });
    }
  }
  return out;
}

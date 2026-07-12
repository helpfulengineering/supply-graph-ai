import { useMemo, useState } from "react";
import type { OkhManifest } from "../../types/okh";
import { deriveCategories, UNCATEGORIZED } from "../okh/categories";
import { formatOkhDisplayTitle } from "../okh/formatOkhDisplayTitle";
import {
  deriveFacetGroups,
  filterItems,
  type FacetSelections,
} from "../okh/facets";
import { normalizeHardwareLicense } from "../okh/normalizeHardwareLicense";

/**
 * List payloads can include sidecars that parse as manifests with empty title
 * and no licensor; only show rows the GET /okh/:id contract can render.
 */
export function isMatchSelectableDesign(item: OkhManifest): boolean {
  if (!item.title?.trim()) return false;
  const lic = item.licensor as unknown;
  if (lic == null) return false;
  if (typeof lic === "string") return lic.trim().length > 0;
  if (Array.isArray(lic)) return lic.length > 0;
  if (typeof lic === "object" && "name" in lic) {
    const n = (lic as { name?: unknown }).name;
    return typeof n === "string" && n.trim().length > 0;
  }
  return false;
}

function textMatches(item: OkhManifest, q: string): boolean {
  if (!q) return true;
  const hay = [
    item.title,
    formatOkhDisplayTitle(item.title),
    item.function,
    item.description,
    ...(item.keywords ?? []),
    ...(item.manufacturing_processes ?? []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(q.trim().toLowerCase());
}

const RESULT_LIMIT = 40;

/**
 * Search + facet filters to pick an OKH design for matching (replaces a bare
 * <select>, which is unusable once the catalog grows).
 */
export function DesignPicker({
  designs,
  selectedId,
  onSelect,
  isLoading,
  isError,
}: {
  designs: OkhManifest[];
  selectedId: string;
  onSelect: (id: string) => void;
  isLoading?: boolean;
  isError?: boolean;
}) {
  const [q, setQ] = useState("");
  const [selections, setSelections] = useState<FacetSelections>({});

  const renderable = useMemo(
    () => designs.filter(isMatchSelectableDesign),
    [designs],
  );

  const selected = useMemo(
    () => renderable.find((d) => d.id === selectedId) ?? null,
    [renderable, selectedId],
  );

  const facetGroups = useMemo(
    () => deriveFacetGroups(renderable, selections),
    [renderable, selections],
  );

  const matched = useMemo(() => {
    const byFacet = filterItems(renderable, selections);
    return byFacet.filter((i) => textMatches(i, q));
  }, [renderable, selections, q]);

  const shown = matched.slice(0, RESULT_LIMIT);

  function clearFilters() {
    setSelections({});
    setQ("");
  }

  const hasFilters = !!q.trim() || Object.values(selections).some((v) => (v?.length ?? 0) > 0);

  return (
    <fieldset className="rounded-lg border border-input p-4">
      <legend className="px-1 text-sm font-medium text-foreground">Design</legend>

      {selected ? (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-indigo-200 bg-indigo-50/70 px-3 py-2 dark:border-indigo-800 dark:bg-indigo-950/30">
          <div className="min-w-0">
            <p className="text-xs text-indigo-700 dark:text-indigo-400">Selected design</p>
            <p className="truncate font-medium text-indigo-950 dark:text-indigo-100">
              {formatOkhDisplayTitle(selected.title)}
            </p>
          </div>
          <button
            type="button"
            className="shrink-0 text-xs text-indigo-700 hover:underline dark:text-indigo-300"
            onClick={() => onSelect("")}
          >
            Clear
          </button>
        </div>
      ) : (
        <p className="mb-3 text-xs text-muted-foreground">
          Search and filter to pick a design to match.
        </p>
      )}

      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading designs…</p>
      )}
      {isError && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Couldn’t load designs. Try refreshing the page.
        </p>
      )}

      {!isLoading && !isError && (
        <div className="space-y-3">
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search designs…"
            aria-label="Search designs"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {facetGroups.map((group) => (
              <label key={group.key} className="block text-sm">
                <span className="mb-1 block text-muted-foreground">{group.label}</span>
                <select
                  aria-label={group.label}
                  className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={(selections[group.key] ?? [])[0] ?? ""}
                  onChange={(e) => {
                    const v = e.target.value;
                    setSelections((prev) => {
                      const next = { ...prev };
                      if (!v) delete next[group.key];
                      else next[group.key] = [v];
                      return next;
                    });
                  }}
                >
                  <option value="">All</option>
                  {group.options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.value} ({o.count})
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>

          {hasFilters && (
            <button
              type="button"
              className="text-xs text-indigo-600 hover:underline dark:text-indigo-400"
              onClick={clearFilters}
            >
              Clear design filters
            </button>
          )}

          {shown.length === 0 ? (
            <p className="rounded-md border border-input px-3 py-2 text-sm text-muted-foreground">
              No designs match the current search/filters.
            </p>
          ) : (
            <div
              role="listbox"
              aria-label="Design search results"
              className="max-h-56 space-y-1 overflow-y-auto rounded-md border border-input p-1"
            >
              {shown.map((d) => {
                const active = d.id === selectedId;
                const category =
                  deriveCategories(d).find((c) => c !== UNCATEGORIZED) ?? null;
                const license = normalizeHardwareLicense(d.license?.hardware);
                return (
                  <button
                    key={d.id}
                    type="button"
                    role="option"
                    aria-selected={active}
                    onClick={() => onSelect(d.id)}
                    className={
                      active
                        ? "flex w-full flex-col items-start rounded-md bg-indigo-100 px-3 py-2 text-left dark:bg-indigo-950/50"
                        : "flex w-full flex-col items-start rounded-md px-3 py-2 text-left hover:bg-accent"
                    }
                  >
                    <span className="text-sm font-medium text-foreground break-words">
                      {formatOkhDisplayTitle(d.title)}
                    </span>
                    <span className="mt-0.5 text-xs text-muted-foreground">
                      {[
                        category,
                        (d.manufacturing_processes ?? []).slice(0, 2).join(", ") || null,
                        license,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            Showing {shown.length}
            {matched.length > RESULT_LIMIT ? ` of ${matched.length}` : ""} design
            {matched.length !== 1 ? "s" : ""}
            {hasFilters ? " (filtered)" : ""}
          </p>
        </div>
      )}
    </fieldset>
  );
}

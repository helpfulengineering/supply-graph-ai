import { useMemo, useState } from "react";
import { FIELD, FIELD_SM, LABEL, LINK_BUTTON } from "../../components/ui/field";
import { Fieldset } from "../../components/ui/Fieldset";
import {
  PANEL_ACCENT,
  PANEL_INSET,
  SCROLL_LIST,
} from "../../components/ui/surface";
import { cn } from "@/lib/utils";
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

  const hasFilters =
    !!q.trim() || Object.values(selections).some((v) => (v?.length ?? 0) > 0);

  return (
    <Fieldset legend="Design">
      {selected ? (
        // PANEL_ACCENT, not FIELD. This read `${FIELD} ... bg-accent/70`,
        // borrowing a form-control class for a banner — so the panel inherited
        // a focus ring it can never show and a text colour it always
        // overrides, and any change to how inputs look would have silently
        // restyled it.
        <div
          className={cn(
            PANEL_ACCENT,
            "mb-3 flex flex-wrap items-center justify-between gap-2 p-3",
          )}
        >
          <div className="min-w-0">
            <p className="text-xs text-primary-ink">Selected design</p>
            <p className="truncate font-medium text-primary-ink">
              {formatOkhDisplayTitle(selected.title)}
            </p>
          </div>
          <button
            type="button"
            className={cn(LINK_BUTTON, "shrink-0")}
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
        <p className="text-sm text-destructive">
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
            className={FIELD}
          />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {facetGroups.map((group) => (
              <label key={group.key} className={LABEL}>
                <span className="mb-1 block text-muted-foreground">
                  {group.label}
                </span>
                <select
                  aria-label={group.label}
                  className={`${FIELD_SM} w-full`}
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
              className={LINK_BUTTON}
              onClick={clearFilters}
            >
              Clear design filters
            </button>
          )}

          {shown.length === 0 ? (
            <p className={cn(PANEL_INSET, "text-sm text-muted-foreground")}>
              No designs match the current search/filters.
            </p>
          ) : (
            <div
              role="listbox"
              aria-label="Design search results"
              className={SCROLL_LIST}
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
                    className={cn(
                      "flex w-full min-w-0 flex-col items-start rounded-md px-3 py-2 text-left transition-colors",
                      active ? "bg-accent" : "hover:bg-accent",
                    )}
                  >
                    <span className="text-sm font-medium text-foreground break-words">
                      {formatOkhDisplayTitle(d.title)}
                    </span>
                    {/*
                      muted-foreground is tuned for the default surface; on the
                      selected row's indigo background it falls to 3.84:1,
                      under the 4.5:1 AA threshold. Darken it when active.
                    */}
                    <span
                      className={
                        active
                          ? "mt-0.5 text-xs text-primary-ink"
                          : "mt-0.5 text-xs text-muted-foreground"
                      }
                    >
                      {[
                        category,
                        (d.manufacturing_processes ?? [])
                          .slice(0, 2)
                          .join(", ") || null,
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
            {matched.length > RESULT_LIMIT ? ` of ${matched.length}` : ""}{" "}
            design
            {matched.length !== 1 ? "s" : ""}
            {hasFilters ? " (filtered)" : ""}
          </p>
        </div>
      )}
    </Fieldset>
  );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useOkhCatalog } from "./useOkhList";
import { OkhCard } from "./OkhCard";
import { OkhListRow } from "./OkhListRow";
import { FacetPanel } from "./FacetPanel";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { Pagination } from "../../components/ui/Pagination";
import { useAuth } from "../../context/AuthContext";
import type { CatalogGroupBy, CatalogSort, CatalogView } from "./catalogBrowse";
import type { OkhManifest } from "../../types/okh";

function SelectControl<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-muted-foreground">
      <span className="whitespace-nowrap">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="rounded-md border border-input bg-background px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function ViewToggle({
  view,
  onChange,
}: {
  view: CatalogView;
  onChange: (v: CatalogView) => void;
}) {
  const btn = (id: CatalogView, label: string) => (
    <button
      type="button"
      aria-pressed={view === id}
      onClick={() => onChange(id)}
      className={
        view === id
          ? "rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white dark:bg-slate-100 dark:text-slate-900"
          : "rounded-md px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
      }
    >
      {label}
    </button>
  );
  return (
    <div
      role="group"
      aria-label="View"
      className="inline-flex rounded-md border border-input p-0.5"
    >
      {btn("catalog", "Catalog")}
      {btn("list", "List")}
    </div>
  );
}

function DesignItems({
  view,
  items,
}: {
  view: CatalogView;
  items: OkhManifest[];
}) {
  if (view === "list") {
    return (
      <div className="rounded-lg border border-slate-200 bg-white px-4 dark:border-slate-700 dark:bg-slate-900">
        {items.map((okh) => (
          <OkhListRow key={okh.id} okh={okh} />
        ))}
      </div>
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((okh) => (
        <OkhCard key={okh.id} okh={okh} />
      ))}
    </div>
  );
}

export function OkhListView() {
  const {
    pageGroups,
    totalItems,
    totalPages,
    safePage,
    facetGroups,
    selections,
    selectedCount,
    filterText,
    view,
    sort,
    groupBy,
    isLoading,
    isError,
    error,
    refetch,
    toggleFacet,
    clearFacets,
    setFilterText,
    setPage,
    setView,
    setSort,
    setGroupBy,
    PAGE_SIZE,
  } = useOkhCatalog();

  const [showFilters, setShowFilters] = useState(false);

  const panel = (
    <FacetPanel
      groups={facetGroups}
      selections={selections}
      selectedCount={selectedCount}
      onToggle={toggleFacet}
      onClear={clearFacets}
    />
  );

  const hasItems = pageGroups.some((g) => g.items.length > 0);
  const { hasWrite } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Open Hardware Designs</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse designs by category and capability, then run facility matching.
          </p>
        </div>
        <Button
          disabled={!hasWrite}
          title={hasWrite ? undefined : "Requires a write-capable API key"}
          onClick={() => navigate("/okh/new")}
        >
          New design
        </Button>
      </div>

      <div className="flex gap-8">
        <aside className="hidden w-60 shrink-0 lg:block">{panel}</aside>

        <div className="min-w-0 flex-1 space-y-4">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <input
                type="search"
                aria-label="Search designs"
                placeholder="Search designs…"
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                className="w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <Button
                variant="outline"
                size="sm"
                className="lg:hidden"
                onClick={() => setShowFilters((v) => !v)}
              >
                Filters{selectedCount > 0 ? ` (${selectedCount})` : ""}
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <ViewToggle view={view} onChange={setView} />
              <SelectControl<CatalogSort>
                label="Sort by"
                value={sort}
                onChange={setSort}
                options={[
                  { value: "alpha", label: "Alphabetical" },
                  { value: "category", label: "Category" },
                ]}
              />
              <SelectControl<CatalogGroupBy>
                label="Group by"
                value={groupBy}
                onChange={setGroupBy}
                options={[
                  { value: "none", label: "None" },
                  { value: "category", label: "Category" },
                  { value: "process", label: "Process" },
                  { value: "license", label: "License" },
                ]}
              />
            </div>
          </div>

          {showFilters && (
            <div className="rounded-lg border p-4 lg:hidden">{panel}</div>
          )}

          {!isLoading && !isError && (
            <p className="text-xs text-muted-foreground">
              {totalItems} design{totalItems !== 1 ? "s" : ""}
              {selectedCount > 0 || filterText ? " (filtered)" : ""}
            </p>
          )}

          {isLoading && <LoadingState message="Loading designs…" />}
          {isError && (
            <ErrorState
              description={error instanceof Error ? error.message : "Failed to load designs."}
              onRetry={() => refetch()}
            />
          )}

          {!isLoading && !isError && !hasItems && (
            <EmptyState
              icon="🔩"
              title="No designs found"
              description={
                selectedCount > 0 || filterText
                  ? "No designs match the current filters."
                  : "No OKH designs are available."
              }
              action={
                selectedCount > 0 || filterText ? (
                  <Button variant="outline" size="sm" onClick={clearFacets}>
                    Clear filters
                  </Button>
                ) : undefined
              }
            />
          )}

          {!isLoading && !isError && hasItems && (
            <>
              <div className="space-y-6">
                {pageGroups.map((group) => (
                  <section key={group.label || "__all__"} className="space-y-3">
                    {group.label ? (
                      <h2 className="text-sm font-semibold text-foreground border-b border-slate-200 pb-1 dark:border-slate-700">
                        {group.label}
                        <span className="ml-2 font-normal text-muted-foreground">
                          ({group.items.length})
                        </span>
                      </h2>
                    ) : null}
                    <DesignItems view={view} items={group.items} />
                  </section>
                ))}
              </div>
              <Pagination
                page={safePage}
                totalPages={totalPages}
                totalItems={totalItems}
                pageSize={PAGE_SIZE}
                onPage={setPage}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

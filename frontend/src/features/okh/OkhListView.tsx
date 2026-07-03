import { useState } from "react";
import { useOkhCatalog } from "./useOkhList";
import { OkhCard } from "./OkhCard";
import { FacetPanel } from "./FacetPanel";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { Pagination } from "../../components/ui/Pagination";

export function OkhListView() {
  const {
    pageItems,
    totalItems,
    totalPages,
    safePage,
    facetGroups,
    selections,
    selectedCount,
    filterText,
    isLoading,
    isError,
    error,
    refetch,
    toggleFacet,
    clearFacets,
    setFilterText,
    setPage,
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Open Hardware Designs</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Browse designs by category and capability, then run facility matching.
        </p>
      </div>

      <div className="flex gap-8">
        {/* Facet sidebar (desktop) */}
        <aside className="hidden w-60 shrink-0 lg:block">{panel}</aside>

        <div className="min-w-0 flex-1 space-y-4">
          {/* Controls */}
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

          {/* Facet panel (mobile disclosure) */}
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

          {!isLoading && !isError && pageItems.length === 0 && (
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

          {!isLoading && !isError && pageItems.length > 0 && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {pageItems.map((okh) => (
                  <OkhCard key={okh.id} okh={okh} />
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

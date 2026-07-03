import { useOkwList } from "./useOkwList";
import { OkwCard } from "./OkwCard";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { Pagination } from "../../components/ui/Pagination";
import { cn } from "@/lib/utils";

function Chip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs transition-colors",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-input bg-background text-foreground hover:bg-accent",
      )}
    >
      {label}
    </button>
  );
}

export function OkwListView() {
  const {
    pageItems,
    totalItems,
    totalPages,
    safePage,
    filterText,
    accessOptions,
    statusOptions,
    selectedAccess,
    selectedStatus,
    filterCount,
    isLoading,
    isError,
    error,
    refetch,
    setPage,
    setFilterText,
    toggleAccess,
    toggleStatus,
    clearFilters,
    PAGE_SIZE,
  } = useOkwList();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Manufacturing Facilities</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Browse facilities (OKW) that can produce open hardware designs.
        </p>
      </div>

      <div className="space-y-3">
        <input
          type="search"
          aria-label="Search facilities"
          placeholder="Search by name, location, or process…"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          className="w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
        {(accessOptions.length > 0 || statusOptions.length > 0) && (
          <div className="flex flex-wrap items-center gap-1.5">
            {accessOptions.map((v) => (
              <Chip key={v} label={v} active={selectedAccess.has(v)} onClick={() => toggleAccess(v)} />
            ))}
            {statusOptions.map((v) => (
              <Chip key={v} label={v} active={selectedStatus.has(v)} onClick={() => toggleStatus(v)} />
            ))}
            {filterCount > 0 && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Clear
              </Button>
            )}
          </div>
        )}
      </div>

      {!isLoading && !isError && (
        <p className="text-xs text-muted-foreground">
          {totalItems} facilit{totalItems !== 1 ? "ies" : "y"}
          {filterCount > 0 || filterText ? " (filtered)" : ""}
        </p>
      )}

      {isLoading && <LoadingState message="Loading facilities…" />}
      {isError && (
        <ErrorState
          description={error instanceof Error ? error.message : "Failed to load facilities."}
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && pageItems.length === 0 && (
        <EmptyState
          icon="🏭"
          title="No facilities found"
          description={
            filterCount > 0 || filterText
              ? "No facilities match the current filters."
              : "No OKW facilities are available yet."
          }
          action={
            filterCount > 0 || filterText ? (
              <Button variant="outline" size="sm" onClick={clearFilters}>
                Clear filters
              </Button>
            ) : undefined
          }
        />
      )}

      {!isLoading && !isError && pageItems.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {pageItems.map((f) => (
              <OkwCard key={f.id} facility={f} />
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
  );
}

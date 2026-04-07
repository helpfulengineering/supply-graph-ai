import { useOkhList } from "./useOkhList";
import { OkhCard } from "./OkhCard";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { EmptyState } from "../../components/ui/EmptyState";
import { Pagination } from "../../components/ui/Pagination";
import type { SortField, SortOrder } from "./useOkhList";

const SORT_OPTIONS: { label: string; field: SortField; order: SortOrder }[] = [
  { label: "Title A→Z", field: "title", order: "asc" },
  { label: "Title Z→A", field: "title", order: "desc" },
  { label: "Version A→Z", field: "version", order: "asc" },
  { label: "Version Z→A", field: "version", order: "desc" },
  { label: "Language A→Z", field: "documentation_language", order: "asc" },
];

export function OkhListView() {
  const {
    pageItems,
    totalItems,
    totalPages,
    safePage,
    filterText,
    sortField,
    sortOrder,
    isLoading,
    isError,
    error,
    refetch,
    setPage,
    handleFilterChange,
    handleSortChange,
    PAGE_SIZE,
  } = useOkhList();

  const selectedSortKey = `${sortField}:${sortOrder}`;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
          Open Hardware Designs
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Browse OKH manifests and run facility matching.
        </p>
      </div>

      {/* Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-400">
            🔍
          </span>
          <input
            type="search"
            placeholder="Filter by title, function, process…"
            value={filterText}
            onChange={(e) => handleFilterChange(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-indigo-500 dark:focus:ring-indigo-900"
          />
        </div>

        {/* Sort */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
            Sort by
          </label>
          <select
            value={selectedSortKey}
            onChange={(e) => {
              const [field, order] = e.target.value.split(":") as [SortField, SortOrder];
              handleSortChange(field, order);
            }}
            className="rounded-lg border border-slate-300 bg-white py-2 pl-3 pr-8 text-sm text-slate-700 focus:border-indigo-400 focus:outline-none dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
          >
            {SORT_OPTIONS.map(({ label, field, order }) => (
              <option key={`${field}:${order}`} value={`${field}:${order}`}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results count */}
      {!isLoading && !isError && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {filterText
            ? `${totalItems} result${totalItems !== 1 ? "s" : ""} matching "${filterText}"`
            : `${totalItems} design${totalItems !== 1 ? "s" : ""} total`}
        </p>
      )}

      {/* States */}
      {isLoading && <LoadingSpinner message="Loading designs…" />}
      {isError && <ErrorMessage error={error} retry={() => refetch()} />}

      {/* Grid */}
      {!isLoading && !isError && pageItems.length === 0 && (
        <EmptyState
          icon="🔩"
          heading="No designs found"
          body={filterText ? `No designs match "${filterText}". Try a different search.` : "No OKH designs are available."}
          action={
            filterText ? (
              <button
                onClick={() => handleFilterChange("")}
                className="rounded-md bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-950 dark:text-indigo-300"
              >
                Clear filter
              </button>
            ) : undefined
          }
        />
      )}

      {!isLoading && !isError && pageItems.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
  );
}

import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchPackageList } from "../../api/package";
import { PackageCard } from "./PackageCard";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { EmptyState } from "../../components/ui/EmptyState";

export function PackageListView() {
  const navigate = useNavigate();

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["package-list"],
    queryFn: () => fetchPackageList(1, 50),
    staleTime: 30_000,
  });

  const packages = data?.items ?? [];
  const total = data?.pagination?.total_items ?? 0;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            Packages
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Point-in-time archives of OKH design files built for local
            inspection and distribution. Each package is a{" "}
            <span className="font-mono text-xs">.tar.gz</span> containing all
            resolved design artefacts.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="shrink-0 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition-colors dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
        >
          {isFetching ? "Refreshing…" : "↻ Refresh"}
        </button>
      </div>

      {/* How-to banner */}
      <div className="rounded-xl border border-indigo-100 bg-indigo-50 px-5 py-4 dark:border-indigo-900 dark:bg-indigo-950/30">
        <p className="text-sm font-medium text-indigo-800 dark:text-indigo-300">
          Building a package
        </p>
        <p className="mt-1 text-sm text-indigo-600 dark:text-indigo-400">
          Open any design in the{" "}
          <button
            onClick={() => navigate("/okh")}
            className="font-semibold underline hover:no-underline"
          >
            Designs
          </button>{" "}
          tab and click{" "}
          <span className="rounded bg-indigo-100 px-1.5 py-0.5 font-mono text-xs dark:bg-indigo-900">
            📦 Build Package
          </span>{" "}
          in the design detail view. The package will then appear in this list.
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-8 dark:border-slate-800 dark:bg-slate-800/30">
          <LoadingSpinner message="Loading packages…" />
        </div>
      )}

      {/* Error */}
      {isError && <ErrorMessage error={error} />}

      {/* Package list */}
      {!isLoading && !isError && (
        <>
          {packages.length === 0 ? (
            <EmptyState
              icon="📦"
              heading="No packages built yet"
              body="Build a package from an OKH design to make it available here for download."
              action={
                <button
                  onClick={() => navigate("/okh")}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 dark:bg-indigo-500"
                >
                  Browse Designs
                </button>
              }
            />
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {total} package{total !== 1 ? "s" : ""} built
              </p>
              <div className="space-y-3">
                {packages.map((pkg) => (
                  <PackageCard
                    key={`${pkg.package_name}@${pkg.version}`}
                    pkg={pkg}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listSolutions } from "../../api/ohm/supply-tree";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { Badge } from "../../components/ui/Badge";

function fmtDate(s: string | null): string {
  if (!s) return "";
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}

export function SolutionsListView() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["solutions"],
    queryFn: listSolutions,
    staleTime: 30_000,
  });

  const solutions = data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Saved Solutions</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Supply-tree solutions saved from matching.
        </p>
      </div>

      {isLoading && <LoadingState message="Loading solutions…" />}
      {isError && (
        <ErrorState
          description={error instanceof Error ? error.message : "Failed to load solutions."}
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && solutions.length === 0 && (
        <EmptyState
          icon="🌳"
          title="No saved solutions"
          description="Run a match to create a supply-tree solution."
          action={
            <Link
              to="/match"
              className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            >
              Go to Match →
            </Link>
          }
        />
      )}

      {!isLoading && !isError && solutions.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {solutions.map((s) => (
            <Link
              key={s.id}
              to={`/visualization/${s.id}`}
              className="group flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-5 no-underline shadow-sm transition-shadow hover:shadow-md dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-slate-800 group-hover:text-indigo-600 dark:text-slate-100 dark:group-hover:text-indigo-400">
                  {s.okh_title || (s.okh_id ? `${s.okh_id.slice(0, 8)}…` : "Untitled solution")}
                </h3>
                <Badge variant={s.score >= 0.8 ? "green" : s.score >= 0.5 ? "yellow" : "red"}>
                  {Math.round(s.score * 100)}%
                </Badge>
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-400 dark:text-slate-500">
                <span>
                  {s.facility_count} facilit{s.facility_count !== 1 ? "ies" : "y"}
                </span>
                <span>
                  {s.tree_count} tree{s.tree_count !== 1 ? "s" : ""}
                </span>
                {fmtDate(s.created_at) && <span>{fmtDate(s.created_at)}</span>}
              </div>
              <span className="mt-1 text-sm font-medium text-indigo-600 dark:text-indigo-400">
                View supply tree →
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

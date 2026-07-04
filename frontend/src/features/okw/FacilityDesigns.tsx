import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchDesignsForFacility } from "../../api/ohm/match";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { Badge } from "../../components/ui/Badge";

/**
 * "Designs this facility can make" — reverse matching (review #7). Runs the
 * design catalog against this one facility and lists the producible designs,
 * ranked by confidence, each linking to the design detail.
 */
export function FacilityDesigns({ okwId }: { okwId: string }) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["facility-designs", okwId],
    queryFn: () => fetchDesignsForFacility(okwId),
    staleTime: 60_000,
  });

  const designs = data?.designs ?? [];

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Designs this facility can make
      </h2>

      {isLoading && <LoadingState message="Checking which designs this facility can make…" />}
      {isError && (
        <ErrorState
          description={error instanceof Error ? error.message : "Failed to load producible designs."}
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && designs.length === 0 && (
        <EmptyState
          icon="🔍"
          title="No producible designs found"
          description="None of the catalog designs currently match this facility’s capabilities."
        />
      )}

      {!isLoading && !isError && designs.length > 0 && (
        <ul className="space-y-2">
          {designs.map((d) => (
            <li key={d.okh_id}>
              <Link
                to={`/okh/${d.okh_id}`}
                className="group flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 no-underline hover:border-indigo-300 hover:bg-indigo-50/40 dark:border-slate-700 dark:hover:border-indigo-700 dark:hover:bg-indigo-950/20"
              >
                <span className="text-sm font-medium text-slate-700 group-hover:text-indigo-600 dark:text-slate-200 dark:group-hover:text-indigo-400">
                  {d.okh_title || d.okh_id}
                </span>
                <Badge
                  variant={d.confidence >= 0.8 ? "green" : d.confidence >= 0.5 ? "yellow" : "red"}
                >
                  {Math.round(d.confidence * 100)}%
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

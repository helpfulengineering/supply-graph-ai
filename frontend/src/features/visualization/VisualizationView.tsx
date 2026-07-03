import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchVisualization } from "../../api/ohm/supply-tree";
import {
  deriveKpis,
  isSolutionEmpty,
  toDependencies,
  toProductionSequence,
} from "./supplyTreeAdapter";
import { KpiCards } from "./KpiCards";
import { SupplyTreeGraph } from "./SupplyTreeGraph";
import { FacilityChart } from "./FacilityChart";
import { ArtifactLinks } from "./ArtifactLinks";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";

export function VisualizationView({ solutionId }: { solutionId: string }) {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["visualization", solutionId],
    queryFn: () => fetchVisualization(solutionId),
    staleTime: 120_000,
  });

  if (isLoading) return <LoadingState message="Loading supply tree…" />;
  if (isError || !data) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Solution not found."}
        onRetry={() => refetch()}
      />
    );
  }
  if (isSolutionEmpty(data)) {
    return (
      <EmptyState
        icon="🌳"
        title="No supply tree"
        description="This solution has no supply tree to visualize."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <button
          onClick={() => navigate(-1)}
          className="mb-2 text-sm text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-bold text-foreground">Supply Tree</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manufacturing plan for the matched solution.
        </p>
      </div>

      <KpiCards kpis={deriveKpis(data)} />

      <div className="grid gap-6 lg:grid-cols-2">
        <SupplyTreeGraph data={data} />
        <FacilityChart data={data} />
      </div>

      {(() => {
        const sequence = toProductionSequence(data);
        const deps = toDependencies(data);
        return (
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Production Sequence
              </h2>
              {sequence.length === 0 ? (
                <p className="text-sm text-slate-400 dark:text-slate-500">
                  No production stages.
                </p>
              ) : (
                <ol className="space-y-2">
                  {sequence.map((stage) => (
                    <li key={stage.index} className="flex items-start gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                        {stage.index}
                      </span>
                      <span className="text-sm text-slate-700 dark:text-slate-200">
                        {stage.items.join(", ")}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Dependencies
              </h2>
              {deps.length === 0 ? (
                <p className="text-sm text-slate-400 dark:text-slate-500">
                  No inter-component dependencies.
                </p>
              ) : (
                <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-200">
                  {deps.map((d) => (
                    <li key={d.node}>
                      <span className="font-medium">{d.node}</span> depends on{" "}
                      {d.dependsOn.join(", ")}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        );
      })()}

      <ArtifactLinks data={data} solutionId={solutionId} />
    </div>
  );
}

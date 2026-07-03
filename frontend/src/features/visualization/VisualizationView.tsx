import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchVisualization } from "../../api/ohm/supply-tree";
import { deriveKpis, isSolutionEmpty } from "./supplyTreeAdapter";
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

      <ArtifactLinks data={data} solutionId={solutionId} />
    </div>
  );
}

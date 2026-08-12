"use client";

import { NetworkIllustration } from "../../components/ui/illustrations";
import { PageHero } from "../../components/layout/PageHero";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { fetchVisualization } from "../../api/ohm/supply-tree";
import {
  deriveKpis,
  isSolutionEmpty,
  toDependencies,
  toProductionSequence,
} from "./supplyTreeAdapter";
import { KpiCards } from "./KpiCards";
import dynamic from "next/dynamic";

// Cytoscape and ECharts are browser-only at module scope; load them client-side.
const SupplyTreeGraph = dynamic(
  () =>
    import("./SupplyTreeGraph").then((m) => ({ default: m.SupplyTreeGraph })),
  { ssr: false },
);
const FacilityChart = dynamic(
  () => import("./FacilityChart").then((m) => ({ default: m.FacilityChart })),
  { ssr: false },
);
import { ArtifactLinks } from "./ArtifactLinks";
import { downloadSolutionJson } from "./downloadSolution";
import {
  LoadingState,
  EmptyState,
  ErrorState,
} from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { SECTION_LABEL } from "../../components/ui/typography";
import { PANEL } from "../../components/ui/surface";
import { cn } from "@/lib/utils";

export function VisualizationView({ solutionId }: { solutionId: string }) {
  const router = useRouter();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["visualization", solutionId],
    queryFn: () => fetchVisualization(solutionId),
  });

  if (isLoading) return <LoadingState message="Loading supply tree…" />;
  if (isError || !data) {
    return (
      <ErrorState
        description={
          error instanceof Error ? error.message : "Solution not found."
        }
        onRetry={() => refetch()}
      />
    );
  }
  if (isSolutionEmpty(data)) {
    return (
      <EmptyState
        icon={<NetworkIllustration className="h-10 w-10" />}
        title="No supply tree"
        description="This solution has no supply tree to visualize."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHero
        title="Supply Tree"
        crumb={[
          { label: "plan" },
          { label: "facilities", href: "/facilities" },
          { label: "dependencies" },
        ]}
        breadcrumb={
          <button
            onClick={() => router.back()}
            className="hover:text-primary-ink"
          >
            ← Back
          </button>
        }
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadSolutionJson(solutionId, data)}
          >
            ⬇ Download JSON
          </Button>
        }
      />

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
            <section className={PANEL}>
              <h2 className={cn(SECTION_LABEL, "mb-4")}>Production Sequence</h2>
              {sequence.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No production stages.
                </p>
              ) : (
                <ol className="space-y-2">
                  {sequence.map((stage) => (
                    <li key={stage.index} className="flex items-start gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-primary-ink">
                        {stage.index}
                      </span>
                      <span className="text-sm text-foreground">
                        {stage.items.join(", ")}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            <section className={PANEL}>
              <h2 className={cn(SECTION_LABEL, "mb-4")}>Dependencies</h2>
              {deps.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No inter-component dependencies.
                </p>
              ) : (
                <ul className="space-y-2 text-sm text-foreground">
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

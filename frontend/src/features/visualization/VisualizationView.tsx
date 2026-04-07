import { Link, useNavigate } from "react-router-dom";
import { useVisualization } from "./useVisualization";
import { KpiCards } from "./KpiCards";
import { SupplyTreeGraph } from "./SupplyTreeGraph";
import { FacilityChart } from "./FacilityChart";
import { ArtifactLinks } from "./ArtifactLinks";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { Badge } from "../../components/ui/Badge";

interface Props {
  solutionId: string;
}

export function VisualizationView({ solutionId }: Props) {
  const { data, isLoading, isError, error, refetch } = useVisualization(solutionId);
  const navigate = useNavigate();

  if (isLoading) return <LoadingSpinner message="Loading visualization…" />;
  if (isError || !data) return <ErrorMessage error={error ?? new Error("Not found")} retry={() => refetch()} />;

  const overview = data.matching.overview;
  const routeHints = data.network.route_hints;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <nav className="mb-2 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <button
              onClick={() => navigate(-1)}
              className="hover:text-indigo-600 dark:hover:text-indigo-400"
            >
              ← Back
            </button>
          </nav>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            Visualization
          </h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <Badge variant="indigo">{overview.matching_mode}</Badge>
            <span className="font-mono text-xs text-slate-400 dark:text-slate-500">
              {solutionId}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
            Generated {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
        <Link
          to={`/match`}
          className="shrink-0 self-start rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          ⚡ New Match
        </Link>
      </div>

      {/* KPIs */}
      <KpiCards data={data} />

      {/* Graph + Chart side by side on wide screens */}
      <div className="grid gap-6 lg:grid-cols-2">
        <SupplyTreeGraph data={data} />
        <FacilityChart data={data} />
      </div>

      {/* Route hints notice */}
      {routeHints.status !== "not_provided" && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/50">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            <span className="font-semibold">Route hints:</span> {routeHints.note}
          </p>
        </div>
      )}

      {/* Artifacts */}
      <ArtifactLinks data={data} solutionId={solutionId} />

      {/* Production sequence */}
      {data.supply_tree.production_sequence.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
          <h3 className="mb-4 text-sm font-semibold text-slate-700 dark:text-slate-300">
            Production Sequence
          </h3>
          <div className="flex flex-wrap items-center gap-2">
            {data.supply_tree.production_sequence.map((stage, i) => (
              <div key={i} className="flex items-center gap-2">
                {i > 0 && <span className="text-slate-300 dark:text-slate-600" aria-hidden="true">→</span>}
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-800">
                  <p className="text-xs text-slate-400 dark:text-slate-500 mb-1">Stage {i + 1}</p>
                  {stage.map((nodeId) => {
                    const node = data.supply_tree.nodes.find((n) => n.id === nodeId);
                    return (
                      <p key={nodeId} className="text-sm font-medium text-slate-700 dark:text-slate-200">
                        {node?.facility_name ?? nodeId.slice(0, 8)}
                      </p>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

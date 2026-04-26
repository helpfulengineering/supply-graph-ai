import { useParams, useNavigate } from "react-router-dom";
import { VisualizationView } from "../features/visualization/VisualizationView";
import { EmptyState } from "../components/ui/EmptyState";

export function VisualizationPage() {
  const { solutionId } = useParams<{ solutionId?: string }>();
  const navigate = useNavigate();

  if (!solutionId) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Visualization</h1>
        <EmptyState
          icon="🗺️"
          heading="No solution selected"
          body="Run a match and save the solution to view its supply chain visualization."
          action={
            <button
              onClick={() => navigate("/okh")}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 dark:bg-indigo-500"
            >
              Browse Designs
            </button>
          }
        />
      </div>
    );
  }

  return <VisualizationView solutionId={solutionId} />;
}

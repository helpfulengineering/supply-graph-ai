import { Navigate, useParams } from "react-router-dom";
import { VisualizationView } from "../features/visualization/VisualizationView";

export function VisualizationPage() {
  const { solutionId } = useParams<{ solutionId?: string }>();
  if (!solutionId) return <Navigate to="/solutions" replace />;
  return <VisualizationView solutionId={solutionId} />;
}

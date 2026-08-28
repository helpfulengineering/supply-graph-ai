"use client";

import { useParams } from "next/navigation";
import { VisualizationView } from "../features/visualization/VisualizationView";

export function VisualizationPage() {
  const { solutionId } = useParams<{ solutionId?: string }>();
  // The bare /visualization route redirects server-side; a missing param here
  // cannot happen through routing.
  if (!solutionId) return null;
  return <VisualizationView solutionId={solutionId} />;
}

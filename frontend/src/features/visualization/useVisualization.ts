import { useQuery } from "@tanstack/react-query";
import { fetchVisualization } from "../../api/supply-tree";
import type { VisualizationData } from "../../types/supply-tree";

export function useVisualization(solutionId: string | undefined) {
  return useQuery<VisualizationData>({
    queryKey: ["visualization", solutionId],
    queryFn: async () => {
      if (!solutionId) throw new Error("No solution ID");
      const res = await fetchVisualization(solutionId);
      return res.data;
    },
    enabled: !!solutionId,
    staleTime: 120_000,
  });
}

import type { VisualizationData } from "../../types/supply-tree";

/** Safe download filename for an exported solution bundle (pure, tested). */
export function solutionFilename(solutionId: string): string {
  const safe = solutionId.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 40) || "solution";
  return `ohm-solution-${safe}.json`;
}

/**
 * Trigger a client-side JSON download of the supply-tree solution bundle.
 *
 * This is the user-owned persistence for a solution now that there's no browse
 * list — save the file, re-open/share it yourself. (User-scoped server history
 * comes with auth.)
 */
export function downloadSolutionJson(solutionId: string, data: VisualizationData): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = solutionFilename(solutionId);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

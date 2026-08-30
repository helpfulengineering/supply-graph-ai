/** Display helpers for async generate-from-url job progress. */

export const TERMINAL_JOB_STATES = new Set(["SUCCESS", "FAILURE", "REVOKED"]);

export function isTerminalJobState(state: string | undefined | null): boolean {
  return Boolean(state && TERMINAL_JOB_STATES.has(state));
}

/**
 * The stages a run reports, in pipeline order.
 *
 * Mirrors `planned_stages()` on the server, which is what makes it possible to
 * say what will happen *before* a run starts rather than only narrating it
 * afterwards. `llm` is conditional there and here: a run told to skip the model
 * never emits it, and promising a stage that will not run is worse than saying
 * nothing.
 */
export const PLANNED_STAGES = [
  "clone",
  "direct",
  "heuristic",
  "nlp",
  "llm",
  "bom_verification",
  "bom_normalization",
  "quality",
  "materials_routing",
] as const;

export function plannedStages(useLlm: boolean): string[] {
  return PLANNED_STAGES.filter((stage) => useLlm || stage !== "llm");
}

/** Exported for the drift check in the tests: labels and planned stages must agree. */
export const STAGE_LABELS: Record<string, string> = {
  clone: "Reading repository",
  direct: "Mapping fields",
  heuristic: "Analysing structure",
  nlp: "Reading documentation",
  llm: "Enhancing with AI",
  bom_verification: "Checking parts lists",
  bom_normalization: "Normalising parts",
  quality: "Assessing quality",
  materials_routing: "Reviewing materials",
};

export function stageLabel(stage: string | null | undefined, state?: string | null): string {
  if (state === "SUCCESS") return "Done";
  if (state === "FAILURE") return "Failed";
  if (state === "REVOKED") return "Cancelled";
  if (state === "PENDING") return "Queued";
  if (!stage) return "Working…";
  return STAGE_LABELS[stage] ?? stage;
}

/** 0–100 for progressbar; terminal success is always 100. */
export function progressPercent(
  state: string | null | undefined,
  fraction: number | null | undefined,
): number {
  if (state === "SUCCESS") return 100;
  if (state === "FAILURE" || state === "REVOKED") {
    return Math.round(Math.max(0, Math.min(1, fraction ?? 0)) * 100);
  }
  return Math.round(Math.max(0, Math.min(1, fraction ?? 0)) * 100);
}

export function aggregatePercent(
  jobs: Array<{ state?: string | null; fraction?: number | null }>,
): number {
  if (jobs.length === 0) return 0;
  const sum = jobs.reduce((acc, j) => acc + progressPercent(j.state, j.fraction), 0);
  return Math.round(sum / jobs.length);
}

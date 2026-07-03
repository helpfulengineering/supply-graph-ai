import { Badge } from "../../components/ui/Badge";
import type { RankedSolution } from "./matchViewModel";
import { confidencePct, confidenceToken } from "./confidence";

export function MatchResultCard({ solution }: { solution: RankedSolution }) {
  const token = confidenceToken(solution.confidence);
  const firstLine = solution.explanation?.split("\n")[0]?.trim() ?? null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 dark:text-slate-500">#{solution.rank}</span>
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">
              {solution.facilityName}
            </h3>
          </div>
          {firstLine && (
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{firstLine}</p>
          )}
        </div>
        <Badge variant={token.variant}>
          {token.label} · {confidencePct(solution.confidence)}%
        </Badge>
      </div>
    </div>
  );
}

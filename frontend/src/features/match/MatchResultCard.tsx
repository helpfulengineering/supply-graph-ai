import { Link } from "react-router-dom";
import { Badge } from "../../components/ui/Badge";
import type { RankedSolution } from "./matchViewModel";
import { confidencePct, confidenceToken } from "./confidence";

export function MatchResultCard({
  solution,
  selected,
  onToggle,
  selectionKey,
}: {
  solution: RankedSolution;
  selected: boolean;
  onToggle: () => void;
  selectionKey: string;
}) {
  const token = confidenceToken(solution.confidence);
  const firstLine = solution.explanation?.split("\n")[0]?.trim() ?? null;
  const treeHref = solution.treeId
    ? `/visualization/${solution.treeId}`
    : null;

  return (
    <div
      className={
        selected
          ? "rounded-xl border border-indigo-300 bg-indigo-50/40 p-5 dark:border-indigo-700 dark:bg-indigo-950/30"
          : "rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
      }
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          className="mt-1 h-4 w-4 accent-indigo-600"
          checked={selected}
          onChange={onToggle}
          aria-label={`Select ${solution.facilityName}`}
          data-selection-key={selectionKey}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-slate-500 dark:text-slate-500">
                  #{solution.rank}
                </span>
                <h3 className="font-semibold text-slate-800 dark:text-slate-100">
                  {solution.facilityName}
                </h3>
              </div>
              {firstLine && (
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  {firstLine}
                </p>
              )}
            </div>
            <Badge variant={token.variant}>
              {token.label} · {confidencePct(solution.confidence)}%
            </Badge>
          </div>
          {treeHref && (
            <div className="mt-3">
              <Link
                to={treeHref}
                className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
              >
                View supply tree →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

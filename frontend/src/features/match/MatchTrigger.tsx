import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchOkhDetail } from "../../api/okh";
import { Badge } from "../../components/ui/Badge";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import type { MatchOptions } from "./useMatch";
import { DEFAULT_MATCH_OPTIONS } from "./useMatch";
import { useState } from "react";
import type { OkhManifest } from "../../types/okh";

interface Props {
  okhId: string;
  onRun: (okhId: string, options: MatchOptions) => void;
  isRunning: boolean;
  hasResult: boolean;
  onReset: () => void;
}

export function MatchTrigger({ okhId, onRun, isRunning, hasResult, onReset }: Props) {
  const [options, setOptions] = useState<MatchOptions>(DEFAULT_MATCH_OPTIONS);

  const { data: okh, isLoading } = useQuery<OkhManifest>({
    queryKey: ["okh-detail", okhId],
    queryFn: () => fetchOkhDetail(okhId),
    staleTime: 120_000,
  });

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
      {/* OKH summary */}
      {isLoading ? (
        <LoadingSpinner message="Loading design…" className="py-6" />
      ) : okh ? (
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
              Selected Design
            </p>
            <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">
              {okh.title || "Untitled Design"}
            </h2>
            {okh.function && (
              <p className="text-sm text-slate-500 dark:text-slate-400 max-w-lg">{okh.function}</p>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {okh.manufacturing_processes.slice(0, 5).map((p) => (
                <Badge key={p} variant="indigo">{p}</Badge>
              ))}
              {okh.materials.length > 0 && (
                <Badge variant="default">{okh.materials.length} material{okh.materials.length !== 1 ? "s" : ""}</Badge>
              )}
            </div>
            <Link
              to={`/okh/${okhId}`}
              className="inline-block text-xs text-indigo-600 hover:underline dark:text-indigo-400"
            >
              View full design →
            </Link>
          </div>

          {/* Options + Run button */}
          <div className="flex flex-col gap-3 sm:items-end">
            <div className="flex flex-col gap-2 text-sm">
              <label className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={options.maxResults}
                  onChange={(e) =>
                    setOptions((o) => ({ ...o, maxResults: Math.max(1, Number(e.target.value)) }))
                  }
                  disabled={isRunning}
                  className="w-16 rounded border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                />
                Max results
              </label>
              <label className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={options.saveSolution}
                  onChange={(e) => setOptions((o) => ({ ...o, saveSolution: e.target.checked }))}
                  disabled={isRunning}
                  className="accent-indigo-600"
                />
                Save solution (for visualization)
              </label>
              <label className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={options.includeHumanSummary}
                  onChange={(e) =>
                    setOptions((o) => ({ ...o, includeHumanSummary: e.target.checked }))
                  }
                  disabled={isRunning}
                  className="accent-indigo-600"
                />
                Include human summary
              </label>
            </div>

            <div className="flex gap-2">
              {hasResult && (
                <button
                  onClick={onReset}
                  disabled={isRunning}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Clear
                </button>
              )}
              <button
                onClick={() => onRun(okhId, options)}
                disabled={isRunning}
                className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60 transition-colors dark:bg-indigo-500 dark:hover:bg-indigo-400"
              >
                {isRunning ? "Running…" : hasResult ? "Re-run Match" : "⚡ Run Match"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No design selected. <Link to="/okh" className="text-indigo-600 hover:underline dark:text-indigo-400">Browse designs</Link>
        </p>
      )}
    </div>
  );
}

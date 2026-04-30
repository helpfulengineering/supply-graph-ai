import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useMatch } from "./useMatch";
import { MatchTrigger } from "./MatchTrigger";
import { MatchResultCard } from "./MatchResultCard";
import { MatchHumanSummary } from "./MatchHumanSummary";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { EmptyState } from "../../components/ui/EmptyState";
import { fetchOkhDetail } from "../../api/okh";
import type { MatchSolution } from "../../types/match";
import type { RfqNavigationState } from "../../types/rfq";
import { MATCH_SESSION } from "./matchSessionKeys";
import { solutionRowId } from "./solutionRowId";

interface Props {
  okhId?: string;
  autoRun?: boolean;
}

function dedupeSolutionsByFacility(input: MatchSolution[]): MatchSolution[] {
  const byFacility = new Map<string, MatchSolution>();
  for (const sol of input) {
    const key = sol.facility_id || sol.facility_name || solutionRowId(sol);
    const existing = byFacility.get(key);
    if (!existing) {
      byFacility.set(key, sol);
      continue;
    }
    // Keep the strongest candidate; stable fallback to earlier rank.
    if (sol.score > existing.score || (sol.score === existing.score && sol.rank < existing.rank)) {
      byFacility.set(key, sol);
    }
  }
  return Array.from(byFacility.values()).sort((a, b) => a.rank - b.rank);
}

function SessionRestoredBanner({
  savedAt,
  onClear,
}: {
  savedAt: Date;
  onClear: () => void;
}) {
  const timeStr = savedAt.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <div className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm dark:border-amber-800 dark:bg-amber-950/30">
      <span className="text-amber-800 dark:text-amber-300">
        <span className="font-medium">Session restored</span>
        <span className="ml-1.5 text-amber-600 dark:text-amber-500">
          — showing results from {timeStr}
        </span>
      </span>
      <button
        onClick={onClear}
        className="ml-4 text-xs font-medium text-amber-700 underline hover:no-underline dark:text-amber-400"
      >
        Clear &amp; start fresh
      </button>
    </div>
  );
}

export function MatchView({ okhId, autoRun = false }: Props) {
  const navigate = useNavigate();

  // selectedIds: local state seeded from sessionStorage
  const [selectedIds, setSelectedIdsState] = useState<Set<string>>(() => {
    try {
      const raw = sessionStorage.getItem(MATCH_SESSION.selected);
      return raw ? new Set(JSON.parse(raw) as string[]) : new Set<string>();
    } catch {
      return new Set<string>();
    }
  });

  const setSelectedIds = useCallback((ids: Set<string>) => {
    setSelectedIdsState(ids);
    try {
      sessionStorage.setItem(MATCH_SESSION.selected, JSON.stringify(Array.from(ids)));
    } catch { /* quota exceeded */ }
  }, []);

  /** Prevents duplicate autorun for the same URL okh_id (e.g. React StrictMode remount). */
  const autorunTargetRef = useRef<string | null>(null);
  // Keep a stable ref so the autoRun effect doesn't re-fire on every render
  // when `trigger` (recreated each render) changes reference.
  const triggerRef = useRef<typeof trigger | null>(null);

  const {
    trigger,
    isLoading,
    isError,
    error,
    hasResult,
    solutions,
    solutionId,
    humanSummary,
    coverageGaps,
    suggestions,
    matchSummaryText,
    processingTime,
    expandedRank,
    toggleExpanded,
    savedAt,
    reset,
  } = useMatch(okhId);

  // Keep ref in sync so autoRun effect always calls the latest trigger.
  triggerRef.current = trigger;
  const displaySolutions = useMemo(() => dedupeSolutionsByFacility(solutions), [solutions]);

  const { data: okhDetail } = useQuery({
    queryKey: ["okh-detail-for-rfq", okhId],
    queryFn: () => fetchOkhDetail(okhId!),
    enabled: !!okhId,
    staleTime: 5 * 60 * 1000,
  });

  const handleSelect = useCallback(
    (rowId: string, checked: boolean) => {
      const next = new Set(selectedIds);
      if (checked) next.add(rowId);
      else next.delete(rowId);
      setSelectedIds(next);
    },
    [selectedIds, setSelectedIds]
  );

  // Also clear selection when session is reset
  const handleReset = useCallback(() => {
    reset();
    setSelectedIds(new Set<string>());
  }, [reset, setSelectedIds]);

  // Reset autorun latch when switching designs so each okh_id can autorun once.
  useEffect(() => {
    autorunTargetRef.current = null;
  }, [okhId]);

  // Auto-trigger match when navigated here from "Run Match ⚡".
  // Skip if we already have session results for this exact OKH — the user
  // can explicitly re-run via the "Re-run Match" button if they want fresh results.
  // `trigger` is intentionally accessed via ref so this effect is NOT re-run
  // every render (trigger changes reference on every render).
  useEffect(() => {
    if (!autoRun || !okhId || hasResult) return;
    if (autorunTargetRef.current === okhId) return;
    autorunTargetRef.current = okhId;
    triggerRef.current?.(okhId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRun, okhId, hasResult]);

  const handleGenerateRfq = useCallback(() => {
    const selectedSolutions = displaySolutions.filter((s) =>
      selectedIds.has(solutionRowId(s))
    );
    const state: RfqNavigationState = {
      okhId: okhId!,
      okhTitle: okhDetail?.title ?? okhId ?? "Unknown Design",
      okhFunction: okhDetail?.function ?? undefined,
      okhVersion: okhDetail?.version ?? undefined,
      solutions: selectedSolutions,
    };
    navigate("/rfq", { state });
  }, [displaySolutions, selectedIds, okhId, okhDetail, navigate]);

  // Prune selected ids when a newer run returns fewer/different unique rows.
  useEffect(() => {
    const valid = new Set(displaySolutions.map((s) => solutionRowId(s)));
    const next = new Set(Array.from(selectedIds).filter((id) => valid.has(id)));
    if (next.size !== selectedIds.size) {
      setSelectedIds(next);
    }
  }, [displaySolutions, selectedIds, setSelectedIds]);

  if (!okhId) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Match Workflow</h1>
        <EmptyState
          icon="⚡"
          heading="No design selected"
          body="Select a design from the browse page to run a facility match."
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

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Match Workflow</h1>
        {solutionId && (
          <div className="flex flex-col items-end gap-1">
            <button
              onClick={() => navigate(`/visualization/${solutionId}`)}
              disabled={selectedIds.size === 0}
              title={
                selectedIds.size === 0
                  ? "Select at least one candidate below to build a supply tree"
                  : "View the supply tree for selected candidates"
              }
              className={[
                "rounded-lg px-4 py-2 text-sm font-semibold text-white transition-colors",
                selectedIds.size > 0
                  ? "bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-400"
                  : "cursor-not-allowed bg-slate-300 dark:bg-slate-700 dark:text-slate-400",
              ].join(" ")}
            >
              🗺️ View Visualization →
            </button>
            {selectedIds.size === 0 && (
              <span className="text-xs text-slate-400 dark:text-slate-500">
                Select a candidate to enable
              </span>
            )}
          </div>
        )}
      </div>

      {/* Match trigger + options */}
      <MatchTrigger
        okhId={okhId}
        onRun={trigger}
        isRunning={isLoading}
        hasResult={hasResult}
        onReset={handleReset}
      />

      {/* Loading state */}
      {isLoading && (
        <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-8 dark:border-indigo-900 dark:bg-indigo-950/30">
          <LoadingSpinner message="Running facility match… this usually takes 10–20 seconds" />
        </div>
      )}

      {/* Error state */}
      {isError && <ErrorMessage error={error} />}

      {/* Session-restored notice */}
      {!isLoading && hasResult && savedAt && (
        <SessionRestoredBanner
          savedAt={savedAt}
          onClear={handleReset}
        />
      )}

      {/* Results */}
      {!isLoading && hasResult && (
        <>
          {/* Human summary */}
          {humanSummary && (
            <MatchHumanSummary
              summary={humanSummary}
              coverageGaps={coverageGaps}
              suggestions={suggestions}
              matchSummaryText={matchSummaryText}
              processingTime={processingTime}
            />
          )}

          {/* Solution ID banner */}
          {solutionId && (
            <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 dark:border-emerald-800 dark:bg-emerald-950/30">
              <div>
                <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300">
                  Solution saved
                </p>
                <p className="font-mono text-xs text-emerald-600 dark:text-emerald-500">
                  {solutionId}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <button
                  onClick={() => navigate(`/visualization/${solutionId}`)}
                  disabled={selectedIds.size === 0}
                  title={
                    selectedIds.size === 0
                      ? "Select at least one candidate to build a supply tree"
                      : "View supply tree"
                  }
                  className={[
                    "rounded-md px-3 py-1.5 text-xs font-semibold text-white transition-colors",
                    selectedIds.size > 0
                      ? "bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500"
                      : "cursor-not-allowed bg-slate-300 dark:bg-slate-700 dark:text-slate-400",
                  ].join(" ")}
                >
                  View Visualization
                </button>
                {selectedIds.size === 0 && (
                  <span className="text-xs text-slate-400 dark:text-slate-500">
                    Select a candidate first
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Results list */}
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {displaySolutions.length} candidate{displaySolutions.length !== 1 ? "s" : ""} — tick to select, click to expand
              </h2>
              {displaySolutions.length > 0 && (
                <button
                  onClick={() => {
                    if (selectedIds.size === displaySolutions.length) {
                      setSelectedIds(new Set<string>());
                    } else {
                      setSelectedIds(new Set(displaySolutions.map((s) => solutionRowId(s))));
                    }
                  }}
                  className="text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  {selectedIds.size === displaySolutions.length ? "Deselect all" : "Select all"}
                </button>
              )}
            </div>

            {displaySolutions.length === 0 ? (
              <EmptyState
                icon="🔍"
                heading="No results returned"
                body="The match completed but found no candidate solutions."
              />
            ) : (
              <div className="space-y-3">
                {displaySolutions.map((sol) => (
                  <MatchResultCard
                    key={solutionRowId(sol)}
                    solution={sol}
                    selectionId={solutionRowId(sol)}
                    isExpanded={expandedRank === sol.rank}
                    onToggle={() => toggleExpanded(sol.rank)}
                    solutionId={solutionId}
                    isSelected={selectedIds.has(solutionRowId(sol))}
                    onSelect={handleSelect}
                  />
                ))}
              </div>
            )}

            {/* Generate RFQ call-to-action */}
            {selectedIds.size > 0 && (
              <div className="mt-4 flex items-center justify-between rounded-xl border border-indigo-200 bg-indigo-50 px-5 py-4 dark:border-indigo-800 dark:bg-indigo-950/30">
                <div>
                  <p className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">
                    {selectedIds.size} facilit{selectedIds.size === 1 ? "y" : "ies"} selected
                  </p>
                  <p className="text-xs text-indigo-600 dark:text-indigo-400">
                    Generate a Request for Quotation document for each
                  </p>
                </div>
                <button
                  onClick={handleGenerateRfq}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors dark:bg-indigo-500 dark:hover:bg-indigo-400"
                >
                  📄 Generate RFQ →
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

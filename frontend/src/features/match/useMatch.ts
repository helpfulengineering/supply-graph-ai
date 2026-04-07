import { useMutation } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { runMatch } from "../../api/match";
import type { MatchResponse, MatchSolution } from "../../types/match";

export interface MatchOptions {
  maxResults: number;
  saveSolution: boolean;
  includeHumanSummary: boolean;
  includeExplanation: boolean;
}

export const DEFAULT_MATCH_OPTIONS: MatchOptions = {
  maxResults: 5,
  saveSolution: true,
  includeHumanSummary: true,
  includeExplanation: true,
};

// ---------------------------------------------------------------------------
// sessionStorage keys — prefix-namespaced to avoid collisions
// ---------------------------------------------------------------------------
const KEY_RESULT = "ohm_v1_match_result";
const KEY_OKH_ID = "ohm_v1_match_okh_id";
const KEY_SAVED_AT = "ohm_v1_match_saved_at";

function readSession<T>(key: string, parse: (raw: string) => T): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? parse(raw) : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useMatch() {
  // Seed from sessionStorage so results survive tab navigation.
  const [result, setResult] = useState<MatchResponse | null>(() =>
    readSession(KEY_RESULT, (raw) => JSON.parse(raw) as MatchResponse)
  );
  const [matchOkhId, setMatchOkhId] = useState<string | null>(() =>
    readSession(KEY_OKH_ID, (raw) => raw)
  );
  const [savedAt, setSavedAt] = useState<Date | null>(() =>
    readSession(KEY_SAVED_AT, (raw) => new Date(raw))
  );
  const [expandedRank, setExpandedRank] = useState<number | null>(null);

  // ---------------------------------------------------------------------------
  // Mirror state → sessionStorage asynchronously (non-blocking).
  // JSON.stringify is intentionally kept out of onSuccess to avoid blocking
  // the React scheduler during mutation settlement.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    try {
      if (result) sessionStorage.setItem(KEY_RESULT, JSON.stringify(result));
      else sessionStorage.removeItem(KEY_RESULT);
    } catch { /* quota exceeded */ }
  }, [result]);

  useEffect(() => {
    try {
      if (matchOkhId) sessionStorage.setItem(KEY_OKH_ID, matchOkhId);
      else sessionStorage.removeItem(KEY_OKH_ID);
    } catch { /* quota exceeded */ }
  }, [matchOkhId]);

  useEffect(() => {
    try {
      if (savedAt) sessionStorage.setItem(KEY_SAVED_AT, savedAt.toISOString());
      else sessionStorage.removeItem(KEY_SAVED_AT);
    } catch { /* quota exceeded */ }
  }, [savedAt]);

  const mutation = useMutation({
    mutationFn: ({
      okhId,
      options,
    }: {
      okhId: string;
      options: MatchOptions;
    }) =>
      runMatch({
        okh_id: okhId,
        max_results: options.maxResults,
        save_solution: options.saveSolution,
        solution_tags: ["demo"],
        solution_ttl_days: 30,
        include_human_summary: options.includeHumanSummary,
        include_explanation: options.includeExplanation,
      }),
    onSuccess: (data, { okhId }) => {
      // Keep onSuccess minimal — only plain setState calls, no synchronous I/O.
      setResult(data);
      setMatchOkhId(okhId);
      setSavedAt(new Date());
      setExpandedRank(null);
    },
  });

  function trigger(okhId: string, options: MatchOptions = DEFAULT_MATCH_OPTIONS) {
    mutation.mutate({ okhId, options });
  }

  function toggleExpanded(rank: number) {
    setExpandedRank((prev) => (prev === rank ? null : rank));
  }

  function reset() {
    mutation.reset();
    setResult(null);
    setMatchOkhId(null);
    setSavedAt(null);
    setExpandedRank(null);
  }

  const solutions: MatchSolution[] = result?.data?.solutions ?? [];
  const solutionId: string | undefined = result?.data?.solution_id;
  const humanSummary = result?.data?.human_summary ?? null;
  const coverageGaps: string[] = result?.data?.coverage_gaps ?? [];
  const suggestions: string[] = result?.data?.suggestions ?? [];
  const matchSummaryText: string = result?.data?.match_summary_text ?? "";
  const processingTime: number | undefined = result?.data?.processing_time;

  return {
    trigger,
    isLoading: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    hasResult: result !== null,
    solutions,
    solutionId,
    humanSummary,
    coverageGaps,
    suggestions,
    matchSummaryText,
    processingTime,
    expandedRank,
    toggleExpanded,
    matchOkhId,
    savedAt,
    reset,
  };
}

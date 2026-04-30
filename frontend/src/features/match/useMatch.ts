import { useMutation } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { runMatch } from "../../api/match";
import type { MatchResponse, MatchSolution } from "../../types/match";
import { MATCH_SESSION } from "./matchSessionKeys";

export interface MatchOptions {
  maxResults: number;
  saveSolution: boolean;
  includeHumanSummary: boolean;
  includeExplanation: boolean;
  allowFacilityCombinations: boolean;
  maxFacilitiesPerSolution: number;
}

export const DEFAULT_MATCH_OPTIONS: MatchOptions = {
  maxResults: 5,
  saveSolution: true,
  includeHumanSummary: true,
  includeExplanation: true,
  allowFacilityCombinations: true,
  maxFacilitiesPerSolution: 10,
};

function readSession<T>(key: string, parse: (raw: string) => T): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? parse(raw) : null;
  } catch {
    return null;
  }
}

function clearStaleSessionFromStorage(urlOkhId: string) {
  const storedOkh = readSession(MATCH_SESSION.okhId, (raw) => raw);
  if (storedOkh && storedOkh !== urlOkhId) {
    try {
      sessionStorage.removeItem(MATCH_SESSION.result);
      sessionStorage.removeItem(MATCH_SESSION.okhId);
      sessionStorage.removeItem(MATCH_SESSION.savedAt);
      sessionStorage.removeItem(MATCH_SESSION.selected);
    } catch {
      /* ignore */
    }
  }
}

function readAllInitial(urlOkhId: string | undefined): {
  result: MatchResponse | null;
  matchOkhId: string | null;
  savedAt: Date | null;
} {
  if (urlOkhId) {
    clearStaleSessionFromStorage(urlOkhId);
  }
  const storedOkh = readSession(MATCH_SESSION.okhId, (raw) => raw);
  if (urlOkhId && storedOkh && storedOkh !== urlOkhId) {
    return { result: null, matchOkhId: null, savedAt: null };
  }
  return {
    result: readSession(MATCH_SESSION.result, (raw) => JSON.parse(raw) as MatchResponse),
    matchOkhId: storedOkh,
    savedAt: readSession(MATCH_SESSION.savedAt, (raw) => new Date(raw)),
  };
}

/**
 * @param urlOkhId - OKH id from the route. When set, persisted results for a *different*
 *   design are ignored and cleared so autorun / Run Match behave correctly.
 */
export function useMatch(urlOkhId?: string) {
  const [{ result, matchOkhId, savedAt }, setCore] = useState(() =>
    readAllInitial(urlOkhId)
  );
  const [expandedRank, setExpandedRank] = useState<number | null>(null);

  // If the URL design changes after mount, drop persisted results for another design.
  useEffect(() => {
    if (!urlOkhId) return;
    if (matchOkhId != null && matchOkhId !== urlOkhId) {
      setCore({ result: null, matchOkhId: null, savedAt: null });
      setExpandedRank(null);
      clearStaleSessionFromStorage(urlOkhId);
    }
  }, [urlOkhId, matchOkhId]);

  useEffect(() => {
    try {
      if (result) sessionStorage.setItem(MATCH_SESSION.result, JSON.stringify(result));
      else sessionStorage.removeItem(MATCH_SESSION.result);
    } catch {
      /* quota exceeded */
    }
  }, [result]);

  useEffect(() => {
    try {
      if (matchOkhId) sessionStorage.setItem(MATCH_SESSION.okhId, matchOkhId);
      else sessionStorage.removeItem(MATCH_SESSION.okhId);
    } catch {
      /* ignore */
    }
  }, [matchOkhId]);

  useEffect(() => {
    try {
      if (savedAt) sessionStorage.setItem(MATCH_SESSION.savedAt, savedAt.toISOString());
      else sessionStorage.removeItem(MATCH_SESSION.savedAt);
    } catch {
      /* ignore */
    }
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
        allow_facility_combinations: options.allowFacilityCombinations,
        max_facilities_per_solution: options.maxFacilitiesPerSolution,
      }),
    onSuccess: (data, { okhId }) => {
      setCore({ result: data, matchOkhId: okhId, savedAt: new Date() });
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
    setCore({ result: null, matchOkhId: null, savedAt: null });
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

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchOkhList } from "../../api/ohm/okh";
import { runMatch } from "../../api/ohm/match";
import { toMatchView } from "./matchViewModel";
import { buildMatchRequest, SYSTEM_MODES, type SystemMode } from "./matchRequest";
import { MatchResultCard } from "./MatchResultCard";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { cn } from "@/lib/utils";

export function MatchView({ okhId, autoRun }: { okhId?: string; autoRun?: boolean }) {
  const designs = useQuery({
    queryKey: ["okh-list"],
    queryFn: () => fetchOkhList({ page: 1, page_size: 100 }),
    staleTime: 60_000,
  });
  const [selected, setSelected] = useState(okhId ?? "");
  const [mode, setMode] = useState<SystemMode>("standard");
  const mutation = useMutation({
    mutationFn: ({ id, m }: { id: string; m: SystemMode }) =>
      runMatch(buildMatchRequest(id, m)),
  });
  const view = useMemo(
    () => (mutation.data ? toMatchView(mutation.data) : null),
    [mutation.data],
  );

  useEffect(() => {
    if (autoRun && okhId) mutation.mutate({ id: okhId, m: "standard" });
    // Run once on mount; MatchPage remounts (via key) when the design changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const renderable = (designs.data?.items ?? []).filter((d) => d.title?.trim());
  const modeInfo = SYSTEM_MODES.find((s) => s.mode === mode);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Match a Design</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Find manufacturing facilities that can produce a design.
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="max-w-md flex-1 text-sm">
            <span className="mb-1 block text-muted-foreground">Design</span>
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              aria-label="Design to match"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Select a design…</option>
              {renderable.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title}
                </option>
              ))}
            </select>
          </label>
          <Button
            disabled={!selected || mutation.isPending}
            onClick={() => mutation.mutate({ id: selected, m: mode })}
          >
            {mutation.isPending ? "Matching…" : "⚡ Run Match"}
          </Button>
        </div>

        <div>
          <span className="mb-1 block text-sm text-muted-foreground">System mode</span>
          <div
            role="radiogroup"
            aria-label="System mode"
            className="inline-flex overflow-hidden rounded-md border border-input"
          >
            {SYSTEM_MODES.map((s) => (
              <button
                key={s.mode}
                type="button"
                role="radio"
                aria-checked={mode === s.mode}
                onClick={() => setMode(s.mode)}
                className={cn(
                  "px-3 py-1.5 text-sm transition-colors",
                  mode === s.mode
                    ? "bg-primary text-primary-foreground"
                    : "bg-background text-foreground hover:bg-accent",
                )}
              >
                {s.label}
              </button>
            ))}
          </div>
          {modeInfo && (
            <p className="mt-1.5 max-w-xl text-xs text-muted-foreground">{modeInfo.description}</p>
          )}
        </div>
      </div>

      {mutation.isPending && <LoadingState message="Matching against facilities…" />}
      {mutation.isError && (
        <ErrorState
          description={mutation.error instanceof Error ? mutation.error.message : "Match failed."}
          onRetry={() => selected && mutation.mutate({ id: selected, m: mode })}
        />
      )}

      {view && !mutation.isPending &&
        (view.solutions.length === 0 ? (
          <EmptyState
            icon="🔍"
            title="No matches found"
            description="No facilities can currently produce this design."
          />
        ) : (
          <div className="space-y-4">
            {view.summary && (
              <p className="rounded-lg border bg-muted/40 p-4 text-sm text-foreground">
                {view.summary}
              </p>
            )}
            {view.coverageGaps.length > 0 && (
              <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4 text-sm dark:border-yellow-800 dark:bg-yellow-950/30">
                <p className="font-medium text-yellow-800 dark:text-yellow-300">Coverage gaps</p>
                <p className="mt-1 text-yellow-700 dark:text-yellow-400">
                  Unmatched: {view.coverageGaps.join(", ")}
                </p>
              </div>
            )}
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                {view.totalSolutions} solution{view.totalSolutions !== 1 ? "s" : ""}
              </p>
              {view.solutionId && (
                <Link
                  to={`/visualization/${view.solutionId}`}
                  className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  View supply tree →
                </Link>
              )}
            </div>
            {view.solutions.map((s, i) => (
              <MatchResultCard key={s.facilityId ?? i} solution={s} />
            ))}
          </div>
        ))}
    </div>
  );
}

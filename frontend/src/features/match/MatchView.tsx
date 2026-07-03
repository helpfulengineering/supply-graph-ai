import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchOkhList } from "../../api/ohm/okh";
import { runMatch } from "../../api/ohm/match";
import { toMatchView } from "./matchViewModel";
import { MatchResultCard } from "./MatchResultCard";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";

export function MatchView({ okhId, autoRun }: { okhId?: string; autoRun?: boolean }) {
  const designs = useQuery({
    queryKey: ["okh-list"],
    queryFn: () => fetchOkhList({ page: 1, page_size: 100 }),
    staleTime: 60_000,
  });
  const [selected, setSelected] = useState(okhId ?? "");
  const mutation = useMutation({ mutationFn: (id: string) => runMatch({ okhId: id }) });
  const view = useMemo(
    () => (mutation.data ? toMatchView(mutation.data) : null),
    [mutation.data],
  );

  useEffect(() => {
    if (autoRun && okhId) mutation.mutate(okhId);
    // Run once on mount; MatchPage remounts (via key) when the design changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const renderable = (designs.data?.items ?? []).filter((d) => d.title?.trim());

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Match a Design</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Find manufacturing facilities that can produce a design.
        </p>
      </div>

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
        <Button disabled={!selected || mutation.isPending} onClick={() => mutation.mutate(selected)}>
          {mutation.isPending ? "Matching…" : "⚡ Run Match"}
        </Button>
      </div>

      {mutation.isPending && <LoadingState message="Matching against facilities…" />}
      {mutation.isError && (
        <ErrorState
          description={mutation.error instanceof Error ? mutation.error.message : "Match failed."}
          onRetry={() => selected && mutation.mutate(selected)}
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
            <p className="text-xs text-muted-foreground">
              {view.totalSolutions} solution{view.totalSolutions !== 1 ? "s" : ""}
            </p>
            {view.solutions.map((s, i) => (
              <MatchResultCard key={s.facilityId ?? i} solution={s} />
            ))}
          </div>
        ))}
    </div>
  );
}

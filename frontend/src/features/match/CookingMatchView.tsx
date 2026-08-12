import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchAllRecipes } from "../../api/ohm/recipes";
import { fetchAllKitchens } from "../../api/ohm/kitchens";
import { runMatch } from "../../api/ohm/match";
import { ApiError } from "../../api/ohm/client";
import { solutionSelectionKey, toMatchView } from "./matchViewModel";
import { defaultTolerance, toleranceCeiling, withinTolerance } from "./nearMiss";
import { buildRecipeMatchRequest, SYSTEM_MODES, type SystemMode } from "./matchRequest";
import { toRfqSolutions } from "./rfqHandoff";
import { RecipePicker } from "./RecipePicker";
import { KitchenFilter } from "./KitchenFilter";
import { MatchResultCard } from "./MatchResultCard";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { cn } from "@/lib/utils";
import type { CookingRfqNavigationState } from "../../types/rfq";

interface Props {
  /** Recipe id to preselect, e.g. from a recipe card/detail page's "Run Match". */
  initialRecipeId?: string;
}

/**
 * Cooking-domain counterpart to MatchView: recipe + kitchens in, ranked
 * solutions out.
 */
export function CookingMatchView({ initialRecipeId }: Props = {}) {
  const navigate = useNavigate();
  const recipes = useQuery({ queryKey: ["recipes"], queryFn: fetchAllRecipes });
  const kitchens = useQuery({ queryKey: ["kitchens"], queryFn: fetchAllKitchens });

  const [selected, setSelected] = useState(initialRecipeId ?? "");
  const [mode, setMode] = useState<SystemMode>("standard");
  const [kitchenIds, setKitchenIds] = useState<string[]>([]);
  const [selectedSolutionKeys, setSelectedSolutionKeys] = useState<string[]>([]);

  const mutation = useMutation({
    mutationFn: ({ id, m, ids }: { id: string; m: SystemMode; ids: string[] }) =>
      runMatch(buildRecipeMatchRequest(id, m, undefined, ids)),
    onSuccess: () => setSelectedSolutionKeys([]),
  });

  const rawView = useMemo(
    () => (mutation.data ? toMatchView(mutation.data) : null),
    [mutation.data],
  );

  const requirementCount = useMemo(
    () =>
      rawView?.solutions.reduce((max, s) => Math.max(max, s.coverage?.total ?? 0), 0) ?? 0,
    [rawView],
  );
  const ceiling = toleranceCeiling(requirementCount);
  const [tolerance, setTolerance] = useState<number | null>(null);
  const effectiveTolerance = Math.min(
    tolerance ?? defaultTolerance(requirementCount),
    ceiling,
  );

  const view = useMemo(() => {
    if (!rawView) return null;
    return {
      ...rawView,
      solutions: rawView.solutions.filter((s) => withinTolerance(s.coverage, effectiveTolerance)),
    };
  }, [rawView, effectiveTolerance]);

  const hiddenCount = (rawView?.solutions.length ?? 0) - (view?.solutions.length ?? 0);
  const modeInfo = SYSTEM_MODES.find((s) => s.mode === mode);
  const canRun = !!selected && kitchenIds.length > 0 && !mutation.isPending;
  const selectedRecipe = recipes.data?.find((r) => r.id === selected);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Match a Recipe</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose a recipe and the kitchens to compare, then run a match.
        </p>
      </div>

      <div className="space-y-4">
        <RecipePicker
          recipes={recipes.data ?? []}
          selectedId={selected}
          onSelect={setSelected}
          isLoading={recipes.isLoading}
          isError={recipes.isError}
        />

        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1">
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
              <p className="mt-1.5 max-w-xl text-xs text-muted-foreground">
                {modeInfo.description}
              </p>
            )}
          </div>
          <Button
            disabled={!canRun}
            onClick={() => mutation.mutate({ id: selected, m: mode, ids: kitchenIds })}
          >
            {mutation.isPending ? "Matching…" : "⚡ Run Match"}
          </Button>
        </div>
        {selected && kitchenIds.length === 0 && (
          <p className="text-xs text-amber-700 dark:text-amber-400">
            Select at least one kitchen below before running a match.
          </p>
        )}
        {!selected && (
          <p className="text-xs text-amber-700 dark:text-amber-400">
            Search and select a recipe above before running a match.
          </p>
        )}

        <KitchenFilter
          kitchens={kitchens.data ?? []}
          selectedIds={kitchenIds}
          onChange={setKitchenIds}
          isLoading={kitchens.isLoading}
          isError={kitchens.isError}
        />
      </div>

      {mutation.isPending && <LoadingState message="Matching against kitchens…" />}
      {mutation.isError && (
        <ErrorState
          description={
            mutation.error instanceof ApiError
              ? [
                  mutation.error.message,
                  mutation.error.requestId ? `Request ID: ${mutation.error.requestId}` : null,
                ]
                  .filter(Boolean)
                  .join(" — ")
              : mutation.error instanceof Error
                ? mutation.error.message
                : "Match failed."
          }
          onRetry={() => canRun && mutation.mutate({ id: selected, m: mode, ids: kitchenIds })}
        />
      )}

      {view &&
        !mutation.isPending &&
        (view.solutions.length === 0 ? (
          <EmptyState
            icon="🔍"
            title="No matches found"
            description="No kitchens can currently make this recipe."
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
                <p className="font-medium text-yellow-800 dark:text-yellow-300">
                  Coverage gaps
                </p>
                <p className="mt-1 text-yellow-700 dark:text-yellow-400">
                  Unmatched: {view.coverageGaps.join(", ")}
                </p>
              </div>
            )}
            {ceiling > 0 && (
              <div className="rounded-lg border border-input bg-muted/30 p-4">
                <label
                  htmlFor="near-miss-tolerance"
                  className="block text-sm font-medium text-foreground"
                >
                  Allow kitchens missing up to{" "}
                  {effectiveTolerance === 0
                    ? "nothing"
                    : `${effectiveTolerance} requirement${effectiveTolerance === 1 ? "" : "s"}`}
                </label>
                <input
                  id="near-miss-tolerance"
                  type="range"
                  min={0}
                  max={ceiling}
                  step={1}
                  value={effectiveTolerance}
                  onChange={(e) => setTolerance(Number(e.target.value))}
                  className="mt-2 w-full max-w-sm"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  This recipe has {requirementCount} requirements. The most you can relax to
                  is {ceiling}, so a result always meets at least two.
                  {hiddenCount > 0 &&
                    ` ${hiddenCount} kitchen${hiddenCount === 1 ? " is" : "s are"} hidden at this setting.`}
                </p>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">
                {view.totalSolutions} solution{view.totalSolutions !== 1 ? "s" : ""}
                {selectedSolutionKeys.length > 0 ? ` · ${selectedSolutionKeys.length} selected` : ""}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={view.solutions.length === 0}
                  onClick={() =>
                    setSelectedSolutionKeys(view.solutions.map((s, i) => solutionSelectionKey(s, i)))
                  }
                >
                  Select all
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={selectedSolutionKeys.length === 0}
                  onClick={() => setSelectedSolutionKeys([])}
                >
                  Clear selection
                </Button>
                <Button
                  size="sm"
                  disabled={selectedSolutionKeys.length === 0 || !selectedRecipe}
                  onClick={() => {
                    const selectedSolutions = view.solutions.filter((s, i) =>
                      selectedSolutionKeys.includes(solutionSelectionKey(s, i)),
                    );
                    const state: CookingRfqNavigationState = {
                      domain: "cooking",
                      recipeId: selectedRecipe!.id,
                      recipeTitle: selectedRecipe!.name,
                      recipe: selectedRecipe,
                      solutions: toRfqSolutions(selectedSolutions),
                    };
                    navigate("/rfq", { state });
                  }}
                >
                  Contact selected kitchens →
                </Button>
              </div>
            </div>
            {view.solutions.map((s, i) => {
              const key = solutionSelectionKey(s, i);
              return (
                <MatchResultCard
                  key={key}
                  solution={s}
                  solutionId={view.solutionId}
                  selectionKey={key}
                  selected={selectedSolutionKeys.includes(key)}
                  onToggle={() =>
                    setSelectedSolutionKeys((prev) =>
                      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
                    )
                  }
                />
              );
            })}
          </div>
        ))}
    </div>
  );
}

import { useMemo, useState } from "react";
import type { Recipe } from "../../types/recipe";

const RESULT_LIMIT = 40;

/**
 * Search + pick a recipe for matching. Deliberately simpler than DesignPicker
 * (no facets): a cooking-domain instance's recipe catalogue is expected to be
 * small — see the cooking-domain-instance plan.
 */
export function RecipePicker({
  recipes,
  selectedId,
  onSelect,
  isLoading,
  isError,
}: {
  recipes: Recipe[];
  selectedId: string;
  onSelect: (id: string) => void;
  isLoading?: boolean;
  isError?: boolean;
}) {
  const [q, setQ] = useState("");

  const selected = useMemo(
    () => recipes.find((r) => r.id === selectedId) ?? null,
    [recipes, selectedId],
  );

  const matched = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return recipes;
    return recipes.filter((r) => r.name.toLowerCase().includes(needle));
  }, [recipes, q]);

  const shown = matched.slice(0, RESULT_LIMIT);

  return (
    <fieldset className="rounded-lg border border-input p-4">
      <legend className="px-1 text-sm font-medium text-foreground">Recipe</legend>

      {selected ? (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-indigo-200 bg-indigo-50/70 px-3 py-2 dark:border-indigo-800 dark:bg-indigo-950/30">
          <div className="min-w-0">
            <p className="text-xs text-indigo-700 dark:text-indigo-400">Selected recipe</p>
            <p className="truncate font-medium text-indigo-950 dark:text-indigo-100">
              {selected.name}
            </p>
          </div>
          <button
            type="button"
            className="shrink-0 text-xs text-indigo-700 hover:underline dark:text-indigo-300"
            onClick={() => onSelect("")}
          >
            Clear
          </button>
        </div>
      ) : (
        <p className="mb-3 text-xs text-muted-foreground">
          Search and pick a recipe to match.
        </p>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">Loading recipes…</p>}
      {isError && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Couldn’t load recipes. Try refreshing the page.
        </p>
      )}

      {!isLoading && !isError && (
        <div className="space-y-3">
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search recipes…"
            aria-label="Search recipes"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />

          {shown.length === 0 ? (
            <p className="rounded-md border border-input px-3 py-2 text-sm text-muted-foreground">
              No recipes match the current search.
            </p>
          ) : (
            <div
              role="listbox"
              aria-label="Recipe search results"
              className="max-h-56 space-y-1 overflow-y-auto rounded-md border border-input p-1"
            >
              {shown.map((r) => {
                const active = r.id === selectedId;
                return (
                  <button
                    key={r.id}
                    type="button"
                    role="option"
                    aria-selected={active}
                    onClick={() => onSelect(r.id)}
                    className={
                      active
                        ? "flex w-full flex-col items-start rounded-md bg-indigo-100 px-3 py-2 text-left dark:bg-indigo-950/50"
                        : "flex w-full flex-col items-start rounded-md px-3 py-2 text-left hover:bg-accent"
                    }
                  >
                    <span className="text-sm font-medium text-foreground break-words">
                      {r.name}
                    </span>
                    <span className="mt-0.5 text-xs text-muted-foreground">
                      {r.ingredients.length} ingredient{r.ingredients.length !== 1 ? "s" : ""}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            Showing {shown.length}
            {matched.length > RESULT_LIMIT ? ` of ${matched.length}` : ""} recipe
            {matched.length !== 1 ? "s" : ""}
          </p>
        </div>
      )}
    </fieldset>
  );
}

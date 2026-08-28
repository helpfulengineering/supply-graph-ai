import { useMemo, useState } from "react";
import type { Recipe } from "../../types/recipe";
import { Fieldset } from "../../components/ui/Fieldset";
import { PANEL_ACCENT } from "../../components/ui/surface";
import { LINK_BUTTON } from "../../components/ui/field";
import { cn } from "@/lib/utils";

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
    <Fieldset legend="Recipe">

      {selected ? (
        <div
          className={cn(
            PANEL_ACCENT,
            "mb-3 flex flex-wrap items-center justify-between gap-2 p-3",
          )}
        >
          <div className="min-w-0">
            <p className="text-xs text-primary-ink">Selected recipe</p>
            <p className="truncate font-medium text-primary-ink">
              {selected.name}
            </p>
          </div>
          <button
            type="button"
            className={cn(LINK_BUTTON, "shrink-0")}
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
        <p className="text-sm text-destructive">
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
                    className={cn(
                      "flex w-full min-w-0 flex-col items-start rounded-md px-3 py-2 text-left transition-colors",
                      active ? "bg-accent" : "hover:bg-accent",
                    )}
                  >
                    <span className="text-sm font-medium text-foreground break-words">
                      {r.name}
                    </span>
                    {/*
                      muted-foreground is tuned for the default surface; on the
                      selected row's indigo background it falls to 3.84:1,
                      under the 4.5:1 AA threshold. Darken it when active.
                      Was a hand-picked indigo shade; primary-ink is the
                      token that encodes the same fix for every tinted surface.
                    */}
                    <span
                      className={
                        active
                          ? "mt-0.5 text-xs text-primary-ink"
                          : "mt-0.5 text-xs text-muted-foreground"
                      }
                    >
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
    </Fieldset>
  );
}

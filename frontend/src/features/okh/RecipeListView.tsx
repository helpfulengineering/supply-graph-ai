import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { fetchAllRecipes } from "../../api/ohm/recipes";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";

/**
 * Cooking-domain recipe browse: list-only (no facets, no create, no detail
 * page — see the cooking-domain-instance plan's "Out of scope"). Recipes are
 * uploaded to storage directly, not created here.
 */
export function RecipeListView() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["recipes"],
    queryFn: fetchAllRecipes,
  });

  const recipes = data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Recipes</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Recipes available for matching on this cooking-domain instance.
        </p>
      </div>

      {isLoading && <LoadingState message="Loading recipes…" />}
      {isError && (
        <ErrorState
          description={error instanceof Error ? error.message : "Failed to load recipes."}
          onRetry={() => refetch()}
        />
      )}
      {!isLoading && !isError && recipes.length === 0 && (
        <EmptyState
          icon="🍳"
          title="No recipes yet"
          description="Upload recipe JSON to this instance's storage under okh/ to see them here."
        />
      )}
      {!isLoading && !isError && recipes.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {recipes.map((recipe) => (
            <div
              key={recipe.id}
              className="group flex flex-col rounded-lg border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md dark:border-slate-700 dark:bg-slate-900"
            >
              <Link to={`/okh/${recipe.id}`} className="flex flex-1 flex-col gap-2 p-4 no-underline">
                <h2 className="font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors dark:text-slate-100 dark:group-hover:text-indigo-400">
                  {recipe.name}
                </h2>
                <p className="text-xs text-muted-foreground">
                  {recipe.ingredients.length} ingredient
                  {recipe.ingredients.length !== 1 ? "s" : ""} ·{" "}
                  {recipe.instructions.length} step{recipe.instructions.length !== 1 ? "s" : ""}
                </p>
              </Link>
              <div className="flex items-center justify-end border-t border-slate-100 px-4 py-2.5 dark:border-slate-800">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/match?recipe_id=${recipe.id}`);
                  }}
                  className="rounded-md bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors dark:bg-indigo-950 dark:text-indigo-300 dark:hover:bg-indigo-900"
                >
                  Run Match ⚡
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

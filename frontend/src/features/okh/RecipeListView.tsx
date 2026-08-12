import { useQuery } from "@tanstack/react-query";
import { fetchAllRecipes } from "../../api/ohm/recipes";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";

/**
 * Cooking-domain recipe browse: list-only (no facets, no create, no detail
 * page — see the cooking-domain-instance plan's "Out of scope"). Recipes are
 * uploaded to storage directly, not created here.
 */
export function RecipeListView() {
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
              className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
            >
              <h2 className="font-semibold text-foreground">{recipe.name}</h2>
              <p className="mt-2 text-xs text-muted-foreground">
                {recipe.ingredients.length} ingredient
                {recipe.ingredients.length !== 1 ? "s" : ""} ·{" "}
                {recipe.instructions.length} step{recipe.instructions.length !== 1 ? "s" : ""}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

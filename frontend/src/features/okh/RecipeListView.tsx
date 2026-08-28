"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { fetchAllRecipes } from "../../api/ohm/recipes";
import { LoadingState, EmptyState, ErrorState } from "../../components/ui/states";
import { DesignsIllustration } from "../../components/ui/illustrations";
import { PAGE_TITLE, CARD_TITLE, BODY_MUTED } from "../../components/ui/typography";

/**
 * Cooking-domain recipe browse: list-only (no facets, no create — see the
 * cooking-domain-instance plan's "Out of scope"). Recipes are uploaded to
 * storage directly, not created here.
 *
 * Drawn from the same card and type roles as OkhCard, which is the
 * manufacturing surface this one mirrors: the two are the same browse against
 * different catalogs, so they should not read as two different apps.
 */
export function RecipeListView() {
  const router = useRouter();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["recipes"],
    queryFn: fetchAllRecipes,
  });

  const recipes = data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className={PAGE_TITLE}>Recipes</h1>
        <p className={`mt-1 ${BODY_MUTED}`}>
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
          icon={<DesignsIllustration className="h-10 w-10" />}
          title="No recipes yet"
          description="Upload recipe JSON to this instance's storage under okh/ to see them here."
        />
      )}
      {!isLoading && !isError && recipes.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {recipes.map((recipe) => (
            <div
              key={recipe.id}
              className="group flex flex-col rounded-xl border border-border bg-card shadow-sm transition-shadow hover:shadow-md"
            >
              <Link
                href={`/okh/${recipe.id}`}
                className="flex flex-1 flex-col gap-2 p-5 no-underline"
              >
                <h2 className={CARD_TITLE}>{recipe.name}</h2>
                <p className="text-xs text-muted-foreground">
                  {recipe.ingredients.length} ingredient
                  {recipe.ingredients.length !== 1 ? "s" : ""} ·{" "}
                  {recipe.instructions.length} step{recipe.instructions.length !== 1 ? "s" : ""}
                </p>
              </Link>
              <div className="flex items-center justify-end border-t border-border px-5 py-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/match?recipe_id=${recipe.id}`);
                  }}
                  className="rounded-md bg-accent px-3 py-1 text-xs font-medium text-primary-ink hover:bg-accent transition-colors"
                >
                  Run Match
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { fetchAllRecipes } from "../../api/ohm/recipes";
import { LoadingState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";

interface Props {
  id: string;
}

/**
 * Cooking-domain counterpart to OkhDetailView. There is no per-recipe fetch
 * endpoint (list-only, see the cooking-domain-instance plan), so this reuses
 * the same ["recipes"] query the list view already populates and looks the
 * recipe up by id -- no extra request for a catalogue this small.
 */
export function RecipeDetailView({ id }: Props) {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["recipes"],
    queryFn: fetchAllRecipes,
  });

  if (isLoading) return <LoadingState message="Loading recipe…" />;

  const recipe = data?.find((r) => r.id === id);

  if (isError || !recipe) {
    return (
      <ErrorState
        description={
          error instanceof Error ? error.message : "Recipe not found."
        }
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-8">
      <nav className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <Link
          to="/okh"
          className="hover:text-indigo-600 dark:hover:text-indigo-400"
        >
          Recipes
        </Link>
        <span aria-hidden="true">›</span>
        <span className="truncate text-slate-700 dark:text-slate-200">
          {recipe.name}
        </span>
      </nav>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
          {recipe.name}
        </h1>
        <Button onClick={() => navigate(`/match?recipe_id=${recipe.id}`)}>
          ⚡ Run Match
        </Button>
      </div>

      <div className="grid gap-8 sm:grid-cols-3">
        <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Ingredients
          </h2>
          {recipe.ingredients.length === 0 ? (
            <p className="text-sm text-muted-foreground">None listed.</p>
          ) : (
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-700 dark:text-slate-200">
              {recipe.ingredients.map((i) => (
                <li key={i}>{i}</li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Instructions
          </h2>
          {recipe.instructions.length === 0 ? (
            <p className="text-sm text-muted-foreground">None listed.</p>
          ) : (
            <ol className="list-inside list-decimal space-y-1 text-sm text-slate-700 dark:text-slate-200">
              {recipe.instructions.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Equipment
          </h2>
          {recipe.equipment.length === 0 ? (
            <p className="text-sm text-muted-foreground">None listed.</p>
          ) : (
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-700 dark:text-slate-200">
              {recipe.equipment.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { fetchAllRecipes } from "../../api/ohm/recipes";
import { LoadingState, ErrorState } from "../../components/ui/states";
import { Button } from "../../components/ui/button";
import { PageHero } from "../../components/layout/PageHero";
import { PANEL } from "../../components/ui/surface";
import { SECTION_LABEL } from "../../components/ui/typography";

interface Props {
  id: string;
}

/** One of the three flat lists the recipe is made of. */
function RecipePanel({
  title,
  items,
  ordered = false,
}: {
  title: string;
  items: readonly string[];
  ordered?: boolean;
}) {
  const List = ordered ? "ol" : "ul";
  return (
    <section className={PANEL}>
      <h2 className={`mb-3 ${SECTION_LABEL}`}>{title}</h2>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">None listed.</p>
      ) : (
        <List
          className={`list-inside space-y-1 text-sm text-foreground ${
            ordered ? "list-decimal" : "list-disc"
          }`}
        >
          {items.map((item, i) => (
            <li key={ordered ? i : item}>{item}</li>
          ))}
        </List>
      )}
    </section>
  );
}

/**
 * Cooking-domain counterpart to OkhDetailView. There is no per-recipe fetch
 * endpoint (list-only, see the cooking-domain-instance plan), so this reuses
 * the same ["recipes"] query the list view already populates and looks the
 * recipe up by id -- no extra request for a catalogue this small.
 */
export function RecipeDetailView({ id }: Props) {
  const router = useRouter();
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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <PageHero
          title={recipe.name}
          breadcrumb={[
            { label: "Recipes", href: "/okh" },
            { label: recipe.name },
          ]}
        />
        <Button onClick={() => router.push(`/match?recipe_id=${recipe.id}`)}>
          Run Match
        </Button>
      </div>

      <div className="grid gap-8 sm:grid-cols-3">
        <RecipePanel title="Ingredients" items={recipe.ingredients} />
        <RecipePanel title="Instructions" items={recipe.instructions} ordered />
        <RecipePanel title="Equipment" items={recipe.equipment} />
      </div>
    </div>
  );
}

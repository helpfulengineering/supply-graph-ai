import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { Recipe } from "../../types/recipe";
import type { Kitchen } from "../../types/kitchen";
import { CookingMatchView } from "./CookingMatchView";

const recipes: Recipe[] = [
  {
    id: "recipe-1",
    name: "Sourdough Bread",
    ingredients: ["flour", "water", "salt", "starter"],
    instructions: ["Mix", "Rest", "Bake"],
    equipment: ["oven"],
    domain: "cooking",
  },
];

const kitchens: Kitchen[] = [];

function renderView(initialRecipeId?: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(["recipes"], recipes);
  client.setQueryData(["kitchens"], kitchens);
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <CookingMatchView initialRecipeId={initialRecipeId} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CookingMatchView", () => {
  it("preselects the recipe passed via initialRecipeId (e.g. from a card's Run Match)", () => {
    renderView("recipe-1");
    expect(screen.getByText("Selected recipe")).toBeInTheDocument();
    // Appears both in the "Selected recipe" banner and the picker's result list.
    expect(screen.getAllByText("Sourdough Bread").length).toBeGreaterThan(0);
  });

  it("has no recipe selected when initialRecipeId is omitted", () => {
    renderView();
    expect(screen.queryByText("Selected recipe")).not.toBeInTheDocument();
  });
});

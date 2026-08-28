import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockRouter } from "../../test/nextNavigation";
import type { Recipe } from "../../types/recipe";
import { RecipeDetailView } from "./RecipeDetailView";

const recipe: Recipe = {
  id: "recipe-1",
  name: "Sourdough Bread",
  ingredients: ["flour", "water", "salt", "starter"],
  instructions: ["Mix", "Rest", "Bake"],
  equipment: ["oven", "mixing bowl"],
  domain: "cooking",
};

function renderDetail(seed: Recipe[] = [recipe]) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(["recipes"], seed);
  return render(
    <QueryClientProvider client={client}>
      <RecipeDetailView id="recipe-1" />
    </QueryClientProvider>,
  );
}

describe("RecipeDetailView", () => {
  it("shows the recipe's ingredients, instructions, and equipment", () => {
    renderDetail();
    expect(
      screen.getByRole("heading", { name: "Sourdough Bread" }),
    ).toBeInTheDocument();
    expect(screen.getByText("flour")).toBeInTheDocument();
    expect(screen.getByText("Mix")).toBeInTheDocument();
    expect(screen.getByText("mixing bowl")).toBeInTheDocument();
  });

  it("links the breadcrumb back to the recipe list", () => {
    renderDetail();
    expect(screen.getByRole("link", { name: /Recipes/i })).toHaveAttribute(
      "href",
      "/okh",
    );
  });

  it("navigates to the recipe's match page via Run Match", async () => {
    const user = userEvent.setup();
    renderDetail();
    await user.click(screen.getByRole("button", { name: /Run Match/i }));
    expect(mockRouter.push).toHaveBeenCalledWith("/match?recipe_id=recipe-1");
  });

  it("shows a not-found error when the id has no matching recipe", () => {
    renderDetail([]);
    expect(screen.getByText(/Recipe not found/i)).toBeInTheDocument();
  });
});

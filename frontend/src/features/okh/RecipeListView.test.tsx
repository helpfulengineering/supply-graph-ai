import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useSearchParams } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { Recipe } from "../../types/recipe";
import { RecipeListView } from "./RecipeListView";

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

function MatchPlaceholder() {
  const [params] = useSearchParams();
  return <div>match:{params.get("recipe_id")}</div>;
}

function renderList() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(["recipes"], recipes);
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/okh"]}>
        <Routes>
          <Route path="/okh" element={<RecipeListView />} />
          <Route path="/okh/:id" element={<div>detail page</div>} />
          <Route path="/match" element={<MatchPlaceholder />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RecipeListView", () => {
  it("links each recipe card to its detail page", () => {
    renderList();
    expect(
      screen.getByRole("link", { name: /Sourdough Bread/i }),
    ).toHaveAttribute("href", "/okh/recipe-1");
  });

  it("navigates to the recipe's match page via Run Match", async () => {
    const user = userEvent.setup();
    renderList();
    await user.click(screen.getByRole("button", { name: /Run Match/i }));
    expect(await screen.findByText("match:recipe-1")).toBeInTheDocument();
  });
});

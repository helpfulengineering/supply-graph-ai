import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { Recipe } from "../../types/recipe";
import type { Kitchen } from "../../types/kitchen";
import type { CookingRfqNavigationState } from "../../types/rfq";
import { server } from "../../test/msw/server";
import { mockRouter } from "../../test/nextNavigation";
import { readNavState } from "../../lib/navState";
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

const kitchens: Kitchen[] = [
  {
    id: "kitchen-1",
    name: "Test Kitchen",
    appliances: ["oven"],
    tools: ["mixing bowl"],
    ingredients: ["flour", "water", "salt"],
    domain: "cooking",
  },
];

/**
 * The RFQ hand-off payload the view just pushed.
 *
 * Under react-router this was a probe component reading `location.state`.
 * Next has no such channel, so the payload is stashed in sessionStorage and
 * the URL carries only its nonce (see lib/navState) — the assertion follows
 * the same path the RFQ page does.
 */
function pushedRfqState(): CookingRfqNavigationState | null {
  const url = mockRouter.push.mock.calls.at(-1)?.[0] as string | undefined;
  if (!url) return null;
  return readNavState<CookingRfqNavigationState>(
    new URL(url, "http://localhost").searchParams.get("h"),
  );
}

function renderView(initialRecipeId?: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(["recipes"], recipes);
  client.setQueryData(["kitchens"], kitchens);
  return render(
    <QueryClientProvider client={client}>
      <CookingMatchView initialRecipeId={initialRecipeId} />
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

  it("navigates to /rfq with cooking nav state when contacting a selected kitchen", async () => {
    server.use(
      http.post("*/v1/api/match", () =>
        HttpResponse.json({
          data: {
            solutions: [
              {
                facility_id: "kitchen-1",
                facility_name: "Test Kitchen",
                confidence: 0.65,
                score: 0.65,
                rank: 1,
                explanation_human: "✓ Test Kitchen MATCHED (confidence: 65%)",
                match_type: "cooking",
              },
            ],
            total_solutions: 1,
          },
        }),
      ),
    );

    const user = userEvent.setup();
    renderView("recipe-1");

    await user.click(screen.getByLabelText("Test Kitchen"));
    await user.click(screen.getByRole("button", { name: "Run Match" }));
    await user.click(await screen.findByLabelText("Select Test Kitchen"));
    await user.click(screen.getByRole("button", { name: "Contact selected kitchens →" }));

    const state = pushedRfqState()!;
    expect(mockRouter.push).toHaveBeenCalledWith(
      expect.stringMatching(/^\/rfq\?h=/),
    );
    expect(state.domain).toBe("cooking");
    expect(state.recipeId).toBe("recipe-1");
    expect(state.recipeTitle).toBe("Sourdough Bread");
    expect(state.solutions).toHaveLength(1);
    expect(state.solutions[0].facility_id).toBe("kitchen-1");
  });

  it("surfaces the tolerance slider instead of a blank empty state when every kitchen is hidden by default tolerance", async () => {
    // 5 requirements, 3 missing: exceeds the default tolerance of 1, so the
    // one and only solution is hidden by `withinTolerance` — but the API DID
    // return a match, so this must not render the "no facilities returned"
    // empty state used when there are truly zero solutions.
    server.use(
      http.post("*/v1/api/match", () =>
        HttpResponse.json({
          data: {
            solutions: [
              {
                facility_id: "kitchen-1",
                facility_name: "Test Kitchen",
                confidence: 0.4,
                score: 0.4,
                rank: 1,
                match_type: "cooking",
                explanation: {
                  requirement_matches: [
                    { requirement_value: "flour", status: "matched" },
                    { requirement_value: "water", status: "matched" },
                    { requirement_value: "salt", status: "not_matched" },
                    { requirement_value: "starter", status: "not_matched" },
                    { requirement_value: "oven", status: "not_matched" },
                  ],
                },
              },
            ],
            total_solutions: 1,
          },
        }),
      ),
    );

    const user = userEvent.setup();
    renderView("recipe-1");

    await user.click(screen.getByLabelText("Test Kitchen"));
    await user.click(screen.getByRole("button", { name: "Run Match" }));

    expect(await screen.findByLabelText(/Allow kitchens missing up to/)).toBeInTheDocument();
    expect(screen.getByText(/1 kitchen is hidden at this setting/)).toBeInTheDocument();
    expect(screen.queryByText("No matches found")).not.toBeInTheDocument();

    const slider = screen.getByLabelText(/Allow kitchens missing up to/) as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "3" } });

    expect(await screen.findByLabelText("Select Test Kitchen")).toBeInTheDocument();
  });
});

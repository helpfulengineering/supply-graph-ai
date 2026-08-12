import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import type { CookingRfqNavigationState } from "../../types/rfq";
import { RfqView } from "./RfqView";

function renderView(navState: CookingRfqNavigationState) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <RfqView navState={navState} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const cookingNavState: CookingRfqNavigationState = {
  domain: "cooking",
  recipeId: "recipe-1",
  recipeTitle: "Chocolate Chip Cookies",
  recipe: {
    id: "recipe-1",
    name: "Chocolate Chip Cookies",
    ingredients: ["flour", "sugar", "chocolate chips"],
    instructions: [],
    equipment: ["oven"],
    domain: "cooking",
  },
  solutions: [
    {
      facility_id: "kitchen-1",
      facility_name: "Test Kitchen",
      confidence: 0.65,
      score: 0.65,
      rank: 1,
      match_type: "cooking",
      explanation: null,
      explanation_human: "✓ Test Kitchen MATCHED (confidence: 65%)",
      metrics: { facility_count: 1, requirement_count: 0, capability_count: 0 },
      tree: {
        id: "tree-1",
        facility_name: "Test Kitchen",
        okh_reference: "",
        confidence_score: 0.65,
        estimated_cost: null,
        estimated_time: null,
        match_type: "cooking",
        depth: 0,
        production_stage: "",
        metadata: {},
      },
      facility: {
        id: "kitchen-1",
        name: "Test Kitchen",
        location: { city: "", country: "" },
        manufacturing_processes: [],
      },
    },
  ],
};

describe("RfqView — cooking domain", () => {
  it("generates a recipe-flavoured RFQ, skipping the OKH manifest fetch", async () => {
    let resolveBody: (body: Record<string, unknown>) => void;
    const bodyPromise = new Promise<Record<string, unknown>>((resolve) => {
      resolveBody = resolve;
    });
    server.use(
      http.post("*/v1/api/rfq/generate", async ({ request }) => {
        resolveBody((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({
          status: "success",
          message: "ok",
          timestamp: new Date().toISOString(),
          data: {
            rfqs: [
              {
                rfq_number: "RFQ-1",
                facility_name: "Test Kitchen",
                facility_id: "kitchen-1",
                confidence: 0.65,
                rank: 1,
                quantity: 1,
                text: "REQUEST FOR QUOTATION",
              },
            ],
            total_rfqs: 1,
            recipe_id: "recipe-1",
            recipe_title: "Chocolate Chip Cookies",
            generated_at: new Date().toISOString(),
          },
        });
      }),
    );

    const user = userEvent.setup();
    renderView(cookingNavState);

    expect(screen.getByText("Chocolate Chip Cookies")).toBeInTheDocument();
    // Cooking uses batch-flavoured quantity wording, not manufacturing's "Production quantity".
    expect(screen.getByText("Batch quantity")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Generate 1 RFQ/ }));

    const body = await bodyPromise;
    expect(body).toMatchObject({
      domain: "cooking",
      recipe_id: "recipe-1",
      recipe_title: "Chocolate Chip Cookies",
    });
    expect(body.okh_id).toBeUndefined();
    expect(body.okh_manifest).toBeUndefined();

    expect(await screen.findByText("RFQ-1", { exact: false })).toBeInTheDocument();
  });
});

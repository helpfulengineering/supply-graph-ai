import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SolutionHierarchy } from "../../api/ohm/supply-tree";
import { ComponentsPanel } from "./ComponentsPanel";

/**
 * The shape the API actually returns.
 *
 * Root components are objects, not ids. Rendering one directly puts an object
 * where React expects a node, which is error #31 — the crash that took down
 * the whole visualization view.
 */
const hierarchy: SolutionHierarchy = {
  root_components: [
    {
      component_id: "frame",
      component_name: "Frame",
      tree_id: "11111111-1111-1111-1111-111111111111",
    },
    {
      component_id: "pump",
      component_name: "Pump assembly",
      tree_id: "22222222-2222-2222-2222-222222222222",
    },
  ],
  component_details: {},
  summary: {
    total_components: 2,
    root_components: 2,
    total_trees: 2,
    max_depth: 3,
  },
};

function renderPanel(data: SolutionHierarchy) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(["solution-hierarchy", "sol-1"], data);
  return render(
    <QueryClientProvider client={client}>
      <ComponentsPanel solutionId="sol-1" />
    </QueryClientProvider>,
  );
}

describe("ComponentsPanel", () => {
  it("renders each root component's name", () => {
    renderPanel(hierarchy);
    expect(screen.getByText("Frame")).toBeInTheDocument();
    expect(screen.getByText("Pump assembly")).toBeInTheDocument();
  });

  it("shows the summary counts", () => {
    renderPanel(hierarchy);
    expect(screen.getByText("Max depth")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("explains an empty root list rather than rendering nothing", () => {
    renderPanel({ ...hierarchy, root_components: [] });
    expect(screen.getByText(/No root components/i)).toBeInTheDocument();
  });
});

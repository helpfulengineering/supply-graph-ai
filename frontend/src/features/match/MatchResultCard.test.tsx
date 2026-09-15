import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MatchResultCard } from "./MatchResultCard";
import type { RankedSolution } from "./matchViewModel";

const solution: RankedSolution = {
  facilityName: "FabLab Drome",
  facilityId: "okw-1",
  confidence: 0.95,
  score: 0.95,
  rank: 1,
  explanation: "✓ FabLab Drome MATCHED\nAll requirements satisfied.",
  treeId: "tree-1",
  facility: null,
  coverage: null,
};

function renderCard(
  props: Partial<Parameters<typeof MatchResultCard>[0]> = {},
) {
  const onToggle = vi.fn();
  render(
    <MatchResultCard
      solution={solution}
      selected={false}
      onToggle={onToggle}
      selectionKey="okw-1"
      {...props}
    />,
  );
  return { onToggle };
}

describe("MatchResultCard", () => {
  it("is selectable", async () => {
    const { onToggle } = renderCard();
    expect(
      screen.getByRole("heading", { name: "FabLab Drome" }),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("checkbox", { name: /select fablab drome/i }),
    );
    expect(onToggle).toHaveBeenCalled();
  });

  // The link previously used the TREE id. The route loads
  // /supply-tree/solution/{id}/visualization, which only accepts a SOLUTION id,
  // so every "View supply tree" link 404'd. Verified against production: a tree
  // id returns 404 where the solution id returns 200.
  // #498 removed the supply-tree link. It addressed a stored solution by id,
  // and solutions are no longer stored — a card is a result you act on now, by
  // selecting it for export or an RFQ.
  it("offers no supply-tree link", () => {
    renderCard();
    expect(
      screen.queryByRole("link", { name: /view supply tree/i }),
    ).toBeNull();
  });
});

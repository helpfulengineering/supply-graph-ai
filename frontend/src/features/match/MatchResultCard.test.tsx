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
      solutionId="sol-1"
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
  it("links by solution id, not tree id", () => {
    renderCard();
    expect(
      screen.getByRole("link", { name: /view supply tree/i }),
    ).toHaveAttribute("href", "/visualization/sol-1");
  });

  it("offers no link when the match was not persisted", () => {
    // Inline manifests are deliberately unsaved, so there is nothing to load.
    renderCard({ solutionId: null });
    expect(
      screen.queryByRole("link", { name: /view supply tree/i }),
    ).toBeNull();
  });
});

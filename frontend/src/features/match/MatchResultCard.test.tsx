import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
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
};

describe("MatchResultCard", () => {
  it("is selectable and links to its own supply tree", async () => {
    const onToggle = vi.fn();
    render(
      <MemoryRouter>
        <MatchResultCard
          solution={solution}
          selected={false}
          onToggle={onToggle}
          selectionKey="okw-1"
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "FabLab Drome" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view supply tree/i })).toHaveAttribute(
      "href",
      "/visualization/tree-1",
    );
    await userEvent.click(screen.getByRole("checkbox", { name: /select fablab drome/i }));
    expect(onToggle).toHaveBeenCalled();
  });
});

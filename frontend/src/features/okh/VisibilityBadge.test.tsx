import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VisibilityBadge } from "./VisibilityBadge";

describe("VisibilityBadge (#576)", () => {
  it.each([
    ["private", "Private"],
    ["members", "Members"],
    ["followers", "Followers"],
    ["public", "Public"],
  ] as const)("labels %s", (level, label) => {
    render(<VisibilityBadge level={level} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("renders nothing when the level is unknown", () => {
    const { container } = render(<VisibilityBadge level={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});

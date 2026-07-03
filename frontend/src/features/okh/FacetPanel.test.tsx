import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FacetPanel } from "./FacetPanel";
import type { FacetGroup } from "./facets";

const groups: FacetGroup[] = [
  {
    key: "process",
    label: "Manufacturing process",
    options: [
      { value: "3D Printing", count: 9 },
      { value: "Laser Cutting", count: 14 },
    ],
  },
  { key: "license", label: "License", options: [{ value: "MIT", count: 6 }] },
];

describe("FacetPanel", () => {
  it("renders groups, options, and counts", () => {
    render(
      <FacetPanel
        groups={groups}
        selections={{}}
        selectedCount={0}
        onToggle={vi.fn()}
        onClear={vi.fn()}
      />,
    );
    expect(screen.getByText("Manufacturing process")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /3D Printing/ })).toBeInTheDocument();
    expect(screen.getByText("14")).toBeInTheDocument();
  });

  it("fires onToggle with the group key and value", async () => {
    const onToggle = vi.fn();
    render(
      <FacetPanel
        groups={groups}
        selections={{}}
        selectedCount={0}
        onToggle={onToggle}
        onClear={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("checkbox", { name: /Laser Cutting/ }));
    expect(onToggle).toHaveBeenCalledWith("process", "Laser Cutting");
  });

  it("reflects selected state and shows Clear all only when something is selected", async () => {
    const onClear = vi.fn();
    const { rerender } = render(
      <FacetPanel
        groups={groups}
        selections={{}}
        selectedCount={0}
        onToggle={vi.fn()}
        onClear={onClear}
      />,
    );
    expect(screen.queryByRole("button", { name: /clear all/i })).toBeNull();

    rerender(
      <FacetPanel
        groups={groups}
        selections={{ license: ["MIT"] }}
        selectedCount={1}
        onToggle={vi.fn()}
        onClear={onClear}
      />,
    );
    expect(screen.getByRole("checkbox", { name: /MIT/ })).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: /clear all/i }));
    expect(onClear).toHaveBeenCalledOnce();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FacilityFilter, type FacilityOption } from "./FacilityFilter";

const facilities: FacilityOption[] = [
  { id: "okw-1", name: "Laser Fab Lab" },
  { id: "okw-2", name: "Community Makerspace" },
  { id: "okw-3", name: "Precision CNC Shop" },
];

describe("FacilityFilter", () => {
  it("summarizes matching against all facilities when nothing is selected", () => {
    render(
      <FacilityFilter facilities={facilities} selectedIds={[]} onChange={() => {}} />,
    );
    expect(screen.getByText(/matching against all facilities/i)).toBeInTheDocument();
  });

  it("toggling a facility reports the new selection", async () => {
    const onChange = vi.fn();
    render(
      <FacilityFilter facilities={facilities} selectedIds={[]} onChange={onChange} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /facilities/i }));
    await userEvent.click(screen.getByLabelText("Precision CNC Shop"));
    expect(onChange).toHaveBeenCalledWith(["okw-3"]);
  });

  it("filters the checklist by the search query", async () => {
    render(
      <FacilityFilter facilities={facilities} selectedIds={[]} onChange={() => {}} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /facilities/i }));
    await userEvent.type(screen.getByLabelText(/filter facilities/i), "cnc");
    expect(screen.getByLabelText("Precision CNC Shop")).toBeInTheDocument();
    expect(screen.queryByLabelText("Laser Fab Lab")).not.toBeInTheDocument();
  });

  it("select all reports every facility id; clear empties it", async () => {
    const onChange = vi.fn();
    render(
      <FacilityFilter facilities={facilities} selectedIds={["okw-1"]} onChange={onChange} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /facilities/i }));
    await userEvent.click(screen.getByRole("button", { name: /select all/i }));
    expect(onChange).toHaveBeenLastCalledWith(["okw-1", "okw-2", "okw-3"]);
    await userEvent.click(screen.getByRole("button", { name: /clear/i }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});

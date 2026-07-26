import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TieredEditor } from "./TieredEditor";

const base = {
  title: "Rover",
  version: "1.0.0",
  function: "Drives around",
  documentation_language: "en",
  licensor: { name: "Ada" },
  license: { hardware: "CC-BY-4.0" },
  manufacturing_processes: ["3D Printing", "Laser Cutting"],
  materials: [{ name: "PLA", quantity: 2 }],
  odd_extra_field: "kept",
};

describe("TieredEditor", () => {
  it("flags required fields that were not extracted", () => {
    render(<TieredEditor manifest={{ ...base, title: "" }} onChange={vi.fn()} />);
    expect(screen.getAllByText("not extracted").length).toBeGreaterThan(0);
  });

  it("edits a nested required leaf by path", async () => {
    const onChange = vi.fn();
    render(<TieredEditor manifest={base} onChange={onChange} />);
    await userEvent.type(screen.getByLabelText("Licensor name"), "!");
    expect(onChange).toHaveBeenCalled();
    const next = onChange.mock.calls.at(-1)![0];
    expect(next.licensor).toEqual({ name: "Ada!" });
  });

  it("renders simple lists as removable chips", async () => {
    const onChange = vi.fn();
    render(<TieredEditor manifest={base} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Remove 3D Printing"));
    expect(onChange.mock.calls.at(-1)![0].manufacturing_processes).toEqual([
      "Laser Cutting",
    ]);
  });

  it("adds a list value", async () => {
    const onChange = vi.fn();
    render(<TieredEditor manifest={base} onChange={onChange} />);
    const input = screen.getByPlaceholderText("Add manufacturing processes…");
    await userEvent.type(input, "Soldering{Enter}");
    expect(onChange.mock.calls.at(-1)![0].manufacturing_processes).toContain("Soldering");
  });

  it("shows nested structures read-only until JSON editing is opened", async () => {
    render(<TieredEditor manifest={base} onChange={vi.fn()} />);
    expect(screen.queryByLabelText("Materials JSON")).not.toBeInTheDocument();
    await userEvent.click(screen.getAllByText("Edit as JSON")[0]);
    expect(screen.getByLabelText("Materials JSON")).toBeInTheDocument();
  });

  it("does not apply broken JSON, and says so", async () => {
    const onChange = vi.fn();
    render(<TieredEditor manifest={base} onChange={onChange} />);
    await userEvent.click(screen.getAllByText("Edit as JSON")[0]);
    const area = screen.getByLabelText("Materials JSON");
    await userEvent.clear(area);
    await userEvent.type(area, "{{ broken");
    expect(screen.getByRole("alert")).toHaveTextContent("Not valid JSON");
  });

  it("never hides an unclassified generated field", async () => {
    render(<TieredEditor manifest={base} onChange={vi.fn()} />);
    const toggle = screen.getByText(/Show everything else/);
    expect(toggle).toHaveTextContent("(1)");
    await userEvent.click(toggle);
    expect(screen.getByLabelText("Odd extra field")).toBeInTheDocument();
  });
});

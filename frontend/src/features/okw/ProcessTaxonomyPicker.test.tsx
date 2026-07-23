import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProcessTaxonomyPicker } from "./ProcessTaxonomyPicker";
import type { TaxonomyProcess } from "./facilityFormModel";

const TAXONOMY: TaxonomyProcess[] = [
  { canonical_id: "3d_printing", display_name: "3D Printing", parent: null, children: ["3d_printing_fdm"] },
  {
    canonical_id: "3d_printing_fdm",
    display_name: "FDM 3D Printing",
    parent: "3d_printing",
    children: [],
  },
  { canonical_id: "cnc_machining", display_name: "CNC Machining", parent: null, children: [] },
];

describe("ProcessTaxonomyPicker", () => {
  it("lists parent processes and expands subtypes when parent selected", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { rerender } = render(
      <ProcessTaxonomyPicker
        taxonomy={TAXONOMY}
        selectedParents={[]}
        selectedSubtypes={[]}
        onChange={onChange}
      />,
    );

    expect(screen.getByLabelText("3D Printing")).toBeInTheDocument();
    expect(screen.queryByLabelText("FDM 3D Printing")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("3D Printing"));
    expect(onChange).toHaveBeenCalledWith({
      parents: ["3d_printing"],
      subtypes: [],
    });

    rerender(
      <ProcessTaxonomyPicker
        taxonomy={TAXONOMY}
        selectedParents={["3d_printing"]}
        selectedSubtypes={[]}
        onChange={onChange}
      />,
    );
    expect(screen.getByLabelText("FDM 3D Printing")).toBeInTheDocument();
  });

  it("selecting a subtype keeps the parent selected", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ProcessTaxonomyPicker
        taxonomy={TAXONOMY}
        selectedParents={["3d_printing"]}
        selectedSubtypes={[]}
        onChange={onChange}
      />,
    );
    await user.click(screen.getByLabelText("FDM 3D Printing"));
    expect(onChange).toHaveBeenCalledWith({
      parents: ["3d_printing"],
      subtypes: ["3d_printing_fdm"],
    });
  });
});

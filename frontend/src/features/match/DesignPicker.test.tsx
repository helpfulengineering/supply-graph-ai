import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { OkhManifest } from "../../types/okh";
import { DesignPicker } from "./DesignPicker";

function design(
  id: string,
  title: string,
  processes: string[],
  license: string,
  keywords: string[] = [],
): OkhManifest {
  return {
    id,
    title,
    version: "1.0.0",
    repo: null,
    function: null,
    description: null,
    intended_use: null,
    keywords,
    documentation_language: "en",
    license: { hardware: license, documentation: null, software: null },
    licensor: { name: "Author", email: null, affiliation: null, social: [] },
    contributors: [],
    manufacturing_processes: processes,
    materials: [],
    design_files: [],
    manufacturing_files: [],
    making_instructions: [],
    parts: [],
    tool_list: [],
    image: null,
    project_link: null,
  };
}

const designs = [
  design("okh-1", "Open-Ventilator", ["3D Printing"], "MIT", ["medical", "mask"]),
  design("okh-2", "Face-Shield", ["Laser Cutting"], "GPL-2.0", ["medical"]),
  design("okh-3", "Lab-Mixer", ["Assembly"], "MIT", ["laboratory"]),
];

describe("DesignPicker", () => {
  it("lets the user search and select a design", async () => {
    const onSelect = vi.fn();
    render(
      <DesignPicker designs={designs} selectedId="" onSelect={onSelect} />,
    );
    await userEvent.type(screen.getByLabelText(/search designs/i), "ventilator");
    expect(screen.getByRole("option", { name: /Open Ventilator/i })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Face Shield/i })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("option", { name: /Open Ventilator/i }));
    expect(onSelect).toHaveBeenCalledWith("okh-1");
  });

  it("shows the selected design and allows clearing it", async () => {
    const onSelect = vi.fn();
    render(
      <DesignPicker designs={designs} selectedId="okh-2" onSelect={onSelect} />,
    );
    expect(screen.getByText("Selected design")).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /Face Shield/i, selected: true }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^Clear$/i }));
    expect(onSelect).toHaveBeenCalledWith("");
  });

  it("filters by category facet", async () => {
    render(
      <DesignPicker designs={designs} selectedId="" onSelect={() => {}} />,
    );
    await userEvent.selectOptions(screen.getByLabelText("Category"), "Laboratory & Bio");
    expect(screen.getByRole("option", { name: /Lab Mixer/i })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Open Ventilator/i })).not.toBeInTheDocument();
  });
});

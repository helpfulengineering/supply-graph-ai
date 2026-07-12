import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { OkhManifest } from "../../types/okh";
import { OkhCard } from "./OkhCard";

function baseOkh(overrides: Partial<OkhManifest> = {}): OkhManifest {
  return {
    id: "4148beb6-aaaa-bbbb-cccc-dddddddddddd",
    title: "3D-Simple-Bias-Tape-Maker",
    version: "1.0.0",
    repo: null,
    function: "A long function text that should not appear on the card anymore.",
    description: "A long description that should not appear on the card anymore.",
    intended_use: null,
    keywords: ["laboratory", "lab"],
    documentation_language: "en",
    license: { hardware: "CC-BY-4.0", documentation: null, software: null },
    licensor: { name: "OSHWA Author", email: null, affiliation: null, social: [] },
    contributors: [],
    manufacturing_processes: ["3DP", "Assembly"],
    materials: [],
    design_files: [],
    manufacturing_files: [],
    making_instructions: [],
    parts: [],
    tool_list: [],
    image: null,
    project_link: null,
    ...overrides,
  };
}

describe("OkhCard", () => {
  it("shows Title Case title, category, processes, author, version, license", () => {
    render(
      <MemoryRouter>
        <OkhCard okh={baseOkh()} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "3D Simple Bias Tape Maker" })).toBeInTheDocument();
    expect(screen.getByText("Laboratory & Bio")).toBeInTheDocument();
    expect(screen.getByText("3DP")).toBeInTheDocument();
    expect(screen.getByText("Assembly")).toBeInTheDocument();
    expect(screen.getByText("OSHWA Author")).toBeInTheDocument();
    expect(screen.getByText("v1.0.0")).toBeInTheDocument();
    expect(screen.getByText("CC-BY-4.0")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run Match/i })).toBeInTheDocument();
  });

  it("does not show description excerpt or truncated UUID", () => {
    render(
      <MemoryRouter>
        <OkhCard okh={baseOkh()} />
      </MemoryRouter>,
    );

    expect(
      screen.queryByText(/should not appear on the card/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/4148beb6/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^EN$/i)).not.toBeInTheDocument();
  });
});

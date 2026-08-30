import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ProvenanceRecord } from "./ProvenanceRecord";
import type { GenerationProvenance } from "./generationProvenance";

const record: GenerationProvenance = {
  schema: "ohm-generation-provenance/v1",
  generated_at: "2026-08-29T12:00:00+00:00",
  source_url: "https://github.com/org/repo",
  stages: [
    { seq: 0, stage: "clone", fraction: 0.12, message: "Cloning", ts: "2026-08-29T12:00:00Z" },
    { seq: 1, stage: "direct", fraction: 0.17, message: null, ts: "2026-08-29T12:00:04Z" },
    { seq: 2, stage: "nlp", fraction: 0.4, message: null, ts: "2026-08-29T12:00:04.200Z" },
  ],
  fields: {
    title: { layer: "direct", method: "metadata_name", confidence: 0.98, source: "metadata.name" },
    description: { layer: "nlp", method: "readme_summary", confidence: 0.62, source: "README.md" },
    version: { layer: "direct", method: "none", confidence: 0, source: "no_version_found" },
  },
};

describe("ProvenanceRecord", () => {
  it("opens on Review, with what needs checking first", () => {
    render(<ProvenanceRecord record={record} />);
    const headings = screen
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent ?? "");
    const notFound = headings.findIndex((t) => t.includes("Nothing was found"));
    const settled = headings.findIndex((t) =>
      t.includes("Read straight from the repository"),
    );
    expect(notFound).toBeGreaterThanOrEqual(0);
    expect(notFound).toBeLessThan(settled);
  });

  it("says a field was not found instead of showing it as zero", () => {
    // "0.00" reads as a measurement; the generator did not measure low
    // confidence here, it found nothing.
    render(<ProvenanceRecord record={record} />);
    expect(screen.getByText("not found")).toBeInTheDocument();
    expect(screen.queryByText("0.00")).not.toBeInTheDocument();
  });

  it("switches to every field, with method and source", async () => {
    const user = userEvent.setup();
    render(<ProvenanceRecord record={record} />);
    await user.click(screen.getByRole("radio", { name: "Fields" }));

    expect(screen.getByText("Every field — 3")).toBeInTheDocument();
    expect(screen.getByText("readme_summary")).toBeInTheDocument();
    expect(screen.getAllByText("method")).toHaveLength(3);
  });

  it("switches to the stages, including one shorter than a poll", async () => {
    // direct ran for 0.2s. A progress bar sampling once a second never shows
    // it; the log is the only place it exists.
    const user = userEvent.setup();
    render(<ProvenanceRecord record={record} />);
    await user.click(screen.getByRole("radio", { name: "Stages" }));

    const stages = screen.getByRole("heading", { name: /What ran/ })
      .parentElement as HTMLElement;
    expect(within(stages).getByText("direct")).toBeInTheDocument();
    expect(within(stages).getByText("0.2s")).toBeInTheDocument();
  });

  it("is one keyboard stop, arrow keys moving between readings", async () => {
    // SegmentedControl's contract; asserted here because the tabs are useless
    // to a keyboard user if this regresses.
    const user = userEvent.setup();
    render(<ProvenanceRecord record={record} />);
    await user.tab();
    await user.tab();
    expect(screen.getByRole("radio", { name: "Review" })).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("radio", { name: "Fields" })).toHaveFocus();
  });

  it("names the repository the record came from", () => {
    render(<ProvenanceRecord record={record} />);
    expect(screen.getByText("https://github.com/org/repo")).toBeInTheDocument();
  });
});

describe("ProvenanceRecord — a run that recorded little", () => {
  const bare: GenerationProvenance = {
    schema: "ohm-generation-provenance/v1",
    generated_at: null,
    source_url: null,
    stages: [{ seq: 0, stage: "clone", fraction: 1, message: null, ts: null }],
    fields: {},
  };

  it("says so on the view that is empty, rather than showing a blank tab", async () => {
    const user = userEvent.setup();
    render(<ProvenanceRecord record={bare} />);
    expect(screen.getByText("This run recorded no fields.")).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "Stages" }));
    expect(screen.getByRole("heading", { name: /What ran/ })).toBeInTheDocument();
  });
});

describe("ProvenanceRecord — watching a run", () => {
  const live = {
    ...record,
    generated_at: null,
    fields: {},
  };

  it("opens on the stages, because that is the view with anything in it", () => {
    // Review would greet a watching reader with "no fields": they arrive only
    // when the run finishes.
    render(<ProvenanceRecord record={live} live />);
    expect(screen.getByRole("heading", { name: /What ran/ })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Stages" })).toBeChecked();
  });

  it("says the run is still going", () => {
    render(<ProvenanceRecord record={live} live />);
    expect(
      // Regex: SectionHeading appends an sr-only "— link to this section"
      // to every heading's accessible name.
      screen.getByRole("heading", { name: /How this design is being generated/ }),
    ).toBeInTheDocument();
  });

  it("marks the last stage as running, not finished", () => {
    // Stages are emitted when they BEGIN, so the newest row is in flight.
    render(<ProvenanceRecord record={live} live />);
    expect(screen.getByText("running")).toBeInTheDocument();
  });

  it("claims nothing is running once the run is over", () => {
    render(<ProvenanceRecord record={record} />);
    expect(screen.queryByText("running")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /How this design was generated/ }),
    ).toBeInTheDocument();
  });

  it("shows the stages a failed run got through", () => {
    // The failure case: not live any more, but the log is the only account of
    // how far it got.
    render(<ProvenanceRecord record={live} />);
    expect(screen.getByRole("radio", { name: "Review" })).toBeChecked();
    expect(screen.getByText("This run recorded no fields.")).toBeInTheDocument();
  });
});

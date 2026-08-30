import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReopenRecord } from "./ReopenRecord";

const record = {
  schema: "ohm-generation-provenance/v1",
  generated_at: "2026-08-29T12:00:00+00:00",
  source_url: "https://github.com/org/repo",
  stages: [{ seq: 0, stage: "clone", fraction: 1, message: null, ts: null }],
  fields: {
    title: {
      layer: "direct",
      method: "metadata_name",
      confidence: 0.98,
      source: "metadata.name",
    },
  },
};

function file(name: string, body: unknown) {
  return new File([JSON.stringify(body)], name, { type: "application/json" });
}

describe("ReopenRecord", () => {
  it("opens a record read from disk, without a server round trip", async () => {
    const onOpen = vi.fn();
    const user = userEvent.setup();
    render(<ReopenRecord onOpen={onOpen} />);

    await user.upload(
      screen.getByLabelText("Generation record"),
      file("run.provenance.json", record),
    );

    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen.mock.calls[0][0].source_url).toBe(
      "https://github.com/org/repo",
    );
  });

  it("names the likely mistake when handed the manifest instead", async () => {
    // The two arrive together from the same download and look alike; "invalid
    // file" would leave the reader guessing which one was wrong.
    const onOpen = vi.fn();
    const user = userEvent.setup();
    render(<ReopenRecord onOpen={onOpen} />);

    await user.upload(
      screen.getByLabelText("Generation record"),
      file("design.okh.json", { title: "A design", version: "1.0.0" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /not a generation record.*\.provenance\.json/i,
    );
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("says so when a .json file does not parse", async () => {
    const onOpen = vi.fn();
    const user = userEvent.setup();
    render(<ReopenRecord onOpen={onOpen} />);

    await user.upload(
      screen.getByLabelText("Generation record"),
      // A .json name, because the input's accept filter is what stops a .txt
      // ever reaching the handler through the picker.
      new File(["{ truncated"], "run.provenance.json", {
        type: "application/json",
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(/not valid JSON/i);
    expect(onOpen).not.toHaveBeenCalled();
  });
});

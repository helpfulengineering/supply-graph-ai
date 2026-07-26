import { describe, expect, it } from "vitest";
import { load } from "js-yaml";
import { filenameStem, serializeManifest } from "./serialize";

const manifest = {
  title: "Open Source Rover",
  version: "1.0.0",
  license: { hardware: "Apache-2.0" },
  manufacturing_processes: ["3D Printing", "Laser Cutting"],
};

describe("filenameStem", () => {
  it("slugifies the title", () => {
    expect(filenameStem(manifest)).toBe("open-source-rover");
  });

  it("falls back when the title is missing or unusable", () => {
    expect(filenameStem({})).toBe("design");
    expect(filenameStem({ title: "!!!" })).toBe("design");
    expect(filenameStem({ title: 42 })).toBe("design");
  });

  it("does not leave stray separators at the edges", () => {
    expect(filenameStem({ title: " -- Rover v2 -- " })).toBe("rover-v2");
  });
});

describe("serializeManifest", () => {
  it("round-trips through YAML without losing structure", () => {
    const { text } = serializeManifest(manifest, "yaml");
    expect(load(text)).toEqual(manifest);
  });

  it("round-trips through JSON without losing structure", () => {
    const { text } = serializeManifest(manifest, "json");
    expect(JSON.parse(text)).toEqual(manifest);
  });

  it("names the file by format", () => {
    expect(serializeManifest(manifest, "yaml").filename).toBe(
      "open-source-rover.okh.yaml",
    );
    expect(serializeManifest(manifest, "json").filename).toBe(
      "open-source-rover.okh.json",
    );
  });

  it("uses the right mime type", () => {
    expect(serializeManifest(manifest, "yaml").mimeType).toBe("application/yaml");
    expect(serializeManifest(manifest, "json").mimeType).toBe("application/json");
  });

  it("emits readable YAML rather than anchors, even with shared references", () => {
    const shared = { hardware: "MIT" };
    const text = serializeManifest(
      { title: "t", license: shared, other: shared },
      "yaml",
    ).text;
    // Anchors (&ref) and aliases (*ref) are valid YAML but unreadable to humans
    // and unsupported by some naive parsers.
    expect(text).not.toContain("&ref");
    expect(text).not.toContain("*ref");
  });

  it("does not wrap long prose mid-sentence", () => {
    const long = "A ventilator ".repeat(30).trim();
    const { text } = serializeManifest({ title: "t", function: long }, "yaml");
    expect(load(text)).toEqual({ title: "t", function: long });
    // The value stays on one line rather than being folded across many.
    const functionLine = text.split("\n").find((l) => l.startsWith("function:"));
    expect(functionLine).toContain("ventilator");
  });

  it("preserves empty collections rather than dropping them", () => {
    const { text } = serializeManifest({ title: "t", materials: [], meta: {} }, "yaml");
    expect(load(text)).toEqual({ title: "t", materials: [], meta: {} });
  });
});

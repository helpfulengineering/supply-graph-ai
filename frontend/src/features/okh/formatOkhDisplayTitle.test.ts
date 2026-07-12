import { describe, expect, it } from "vitest";
import { formatOkhDisplayTitle } from "./formatOkhDisplayTitle";

describe("formatOkhDisplayTitle", () => {
  it("title-cases kebab-case slugs with spaces", () => {
    expect(formatOkhDisplayTitle("3D-Simple-Bias-Tape-Maker")).toBe(
      "3D Simple Bias Tape Maker",
    );
  });

  it("title-cases snake_case", () => {
    expect(formatOkhDisplayTitle("open_source_rover")).toBe("Open Source Rover");
  });

  it("preserves hardware acronyms", () => {
    expect(formatOkhDisplayTitle("3dp-iso-8655-compliant-multichannel-pipette")).toBe(
      "3DP ISO 8655 Compliant Multichannel Pipette",
    );
    expect(formatOkhDisplayTitle("pcb-led-fixture")).toBe("PCB LED Fixture");
  });

  it("leaves already-spaced titles readable", () => {
    expect(formatOkhDisplayTitle("Open Ventilator")).toBe("Open Ventilator");
  });

  it("handles empty input", () => {
    expect(formatOkhDisplayTitle("")).toBe("Untitled Design");
    expect(formatOkhDisplayTitle(null)).toBe("Untitled Design");
  });
});

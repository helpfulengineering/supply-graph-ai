import { describe, expect, it } from "vitest";
import {
  aggregatePercent,
  isTerminalJobState,
  progressPercent,
  stageLabel,
} from "./jobProgress";

describe("jobProgress", () => {
  it("treats SUCCESS/FAILURE/REVOKED as terminal", () => {
    expect(isTerminalJobState("SUCCESS")).toBe(true);
    expect(isTerminalJobState("PROGRESS")).toBe(false);
  });

  it("maps known stages to readable labels", () => {
    expect(stageLabel("llm", "PROGRESS")).toMatch(/AI/i);
    expect(stageLabel(null, "SUCCESS")).toBe("Done");
  });

  it("clamps progress and averages across jobs", () => {
    expect(progressPercent("PROGRESS", 0.5)).toBe(50);
    expect(progressPercent("SUCCESS", 0.2)).toBe(100);
    expect(
      aggregatePercent([
        { state: "SUCCESS", fraction: 1 },
        { state: "PROGRESS", fraction: 0.5 },
      ]),
    ).toBe(75);
  });
});

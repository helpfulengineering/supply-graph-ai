import { describe, expect, it } from "vitest";
import {
  aggregatePercent,
  isTerminalJobState,
  progressPercent,
  stageLabel,
  PLANNED_STAGES,
  plannedStages,
  STAGE_LABELS,
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

describe("the planned stage list", () => {
  it("names every stage it plans", () => {
    // The panel shown before a run reads these labels. A stage without one
    // would render its raw pipeline name at a user.
    for (const stage of PLANNED_STAGES) {
      expect(stageLabel(stage)).not.toBe(stage);
    }
  });

  it("has a label for nothing it does not plan", () => {
    // The other direction: a label left behind after a stage is removed is a
    // promise the pipeline no longer keeps.
    const labelled = Object.keys(STAGE_LABELS);
    expect([...labelled].sort()).toEqual([...PLANNED_STAGES].sort());
  });

  it("drops the model stage when a run is told to skip it", () => {
    expect(plannedStages(true)).toContain("llm");
    expect(plannedStages(false)).not.toContain("llm");
    expect(plannedStages(false)).toHaveLength(PLANNED_STAGES.length - 1);
  });
});

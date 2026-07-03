import { describe, expect, it } from "vitest";
import { confidencePct, confidenceToken } from "./confidence";

describe("confidenceToken", () => {
  it("buckets scores into High/Medium/Low", () => {
    expect(confidenceToken(0.95).label).toBe("High");
    expect(confidenceToken(0.8).variant).toBe("green");
    expect(confidenceToken(0.6).label).toBe("Medium");
    expect(confidenceToken(0.3).variant).toBe("red");
  });
});

describe("confidencePct", () => {
  it("converts and clamps to a percentage", () => {
    expect(confidencePct(0.923)).toBe(92);
    expect(confidencePct(1.5)).toBe(100);
    expect(confidencePct(-1)).toBe(0);
  });
});

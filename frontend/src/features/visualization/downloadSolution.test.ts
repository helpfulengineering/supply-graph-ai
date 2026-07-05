import { describe, expect, it } from "vitest";
import { solutionFilename } from "./downloadSolution";

describe("solutionFilename", () => {
  it("builds a namespaced .json filename from the solution id", () => {
    expect(solutionFilename("sol-1")).toBe("ohm-solution-sol-1.json");
  });

  it("sanitizes unsafe characters (e.g. a MoM IRI-like id)", () => {
    expect(solutionFilename("urn:mak:space/x")).toBe("ohm-solution-urnmakspacex.json");
  });

  it("falls back when the id has no safe characters", () => {
    expect(solutionFilename("///")).toBe("ohm-solution-solution.json");
  });
});

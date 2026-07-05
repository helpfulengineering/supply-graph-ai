import { describe, expect, it } from "vitest";
import { buildMatchRequest } from "./matchRequest";

describe("buildMatchRequest", () => {
  it("maps minimal to relaxed params", () => {
    expect(buildMatchRequest("okh-1", "minimal")).toMatchObject({
      okhId: "okh-1",
      qualityLevel: "hobby",
      strictMode: false,
    });
  });

  it("maps standard to the professional default", () => {
    expect(buildMatchRequest("okh-1", "standard")).toMatchObject({
      qualityLevel: "professional",
      strictMode: false,
    });
  });

  it("maps strict to enforced params", () => {
    expect(buildMatchRequest("okh-1", "strict")).toMatchObject({
      qualityLevel: "medical",
      strictMode: true,
    });
  });

  it("passes through maxResults", () => {
    expect(buildMatchRequest("okh-1", "standard", 5).maxResults).toBe(5);
  });

  it("includes okwIds when a facility subset is chosen", () => {
    expect(buildMatchRequest("okh-1", "standard", undefined, ["a", "b"]).okwIds).toEqual([
      "a",
      "b",
    ]);
  });

  it("omits okwIds when the subset is empty (match all facilities)", () => {
    expect(buildMatchRequest("okh-1", "standard", undefined, [])).not.toHaveProperty("okwIds");
    expect(buildMatchRequest("okh-1", "standard")).not.toHaveProperty("okwIds");
  });

  it("a network filter supersedes okwIds", () => {
    const req = buildMatchRequest("okh-1", "standard", undefined, ["a"], {
      country: "FR",
      include_mom: true,
    });
    expect(req.networkFilter).toEqual({ country: "FR", include_mom: true });
    expect(req).not.toHaveProperty("okwIds");
  });
});

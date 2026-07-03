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
});

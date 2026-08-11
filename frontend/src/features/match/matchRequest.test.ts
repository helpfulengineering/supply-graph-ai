import { describe, expect, it } from "vitest";
import {
  buildInlineMatchRequest,
  buildMatchRequest,
  buildRecipeMatchRequest,
} from "./matchRequest";

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

  it("a network filter can combine with okwIds for a MoM/local subset", () => {
    const req = buildMatchRequest("okh-1", "standard", undefined, ["a"], {
      country: "FR",
      include_mom: true,
    });
    expect(req.networkFilter).toEqual({ country: "FR", include_mom: true });
    expect(req.okwIds).toEqual(["a"]);
  });

  it("passes MoM space IRIs through as okwIds (network space ids)", () => {
    const momIri = "https://maps.ofmaking.org/space/example-lab";
    const localId = "b2222222-2222-4222-8222-222222222222";
    const req = buildMatchRequest(
      "okh-1",
      "standard",
      undefined,
      [momIri, localId],
      { include_mom: true },
    );
    expect(req.okwIds).toEqual([momIri, localId]);
    expect(req.networkFilter).toEqual({ include_mom: true });
  });
});

describe("buildInlineMatchRequest", () => {
  const manifest = { title: "Generated", manufacturing_processes: ["3D Printing"] };

  it("sends the manifest instead of an id", () => {
    const req = buildInlineMatchRequest(manifest, "standard");
    expect(req.okhManifest).toEqual(manifest);
    expect(req.okhId).toBeUndefined();
  });

  it("carries the system mode through, like the id-based builder", () => {
    const inline = buildInlineMatchRequest(manifest, "strict");
    const byId = buildMatchRequest("okh-1", "strict");
    expect(inline.qualityLevel).toBe(byId.qualityLevel);
    expect(inline.strictMode).toBe(byId.strictMode);
  });

  it("supports a network filter and a facility subset together", () => {
    const req = buildInlineMatchRequest(manifest, "standard", 5, ["f1"], {
      country: "France",
    });
    expect(req.networkFilter).toEqual({ country: "France" });
    expect(req.okwIds).toEqual(["f1"]);
    expect(req.maxResults).toBe(5);
  });

  it("omits an empty facility subset", () => {
    expect(buildInlineMatchRequest(manifest, "standard", undefined, []).okwIds).toBeUndefined();
  });
});

describe("buildRecipeMatchRequest", () => {
  it("sends a recipeId instead of an okhId", () => {
    const req = buildRecipeMatchRequest("recipe-1", "standard");
    expect(req.recipeId).toBe("recipe-1");
    expect(req.okhId).toBeUndefined();
  });

  it("carries the system mode through, like the OKH builder", () => {
    const recipe = buildRecipeMatchRequest("recipe-1", "strict");
    const okh = buildMatchRequest("okh-1", "strict");
    expect(recipe.qualityLevel).toBe(okh.qualityLevel);
    expect(recipe.strictMode).toBe(okh.strictMode);
  });

  it("includes okwIds when a kitchen subset is chosen", () => {
    expect(
      buildRecipeMatchRequest("recipe-1", "standard", undefined, ["k1", "k2"]).okwIds,
    ).toEqual(["k1", "k2"]);
  });

  it("omits okwIds when the subset is empty (match all kitchens)", () => {
    expect(buildRecipeMatchRequest("recipe-1", "standard", undefined, [])).not.toHaveProperty(
      "okwIds",
    );
  });
});

import { describe, expect, it } from "vitest";
import { qualityLabel, toQualityBanner } from "./qualityBanner";

describe("qualityLabel", () => {
  it("renders a fraction as a percentage", () => {
    expect(qualityLabel(0.82)).toBe("82%");
  });

  it("renders a percentage as a percentage", () => {
    expect(qualityLabel(82)).toBe("82%");
  });

  it("humanises an enum-ish string", () => {
    expect(qualityLabel("needs_review")).toBe("needs review");
  });

  it("returns null when absent", () => {
    expect(qualityLabel(null)).toBeNull();
    expect(qualityLabel(undefined)).toBeNull();
  });
});

describe("toQualityBanner", () => {
  it("warns, never blocks, when required fields are missing", () => {
    const b = toQualityBanner({ missing_required_fields: ["title", "version"] });
    expect(b.tone).toBe("warn");
    expect(b.missingRequired).toEqual(["title", "version"]);
    expect(b.headline).toContain("2 required fields");
  });

  it("uses singular phrasing for one missing field", () => {
    const b = toQualityBanner({ missing_required_fields: ["title"] });
    expect(b.headline).toContain("1 required field ");
    expect(b.headline).toContain("fill it in");
  });

  it("reports good when nothing is missing", () => {
    const b = toQualityBanner({
      missing_required_fields: [],
      overall_quality: 0.9,
    });
    expect(b.tone).toBe("good");
    expect(b.headline).toContain("90%");
  });

  it("handles a good report with no quality figure", () => {
    const b = toQualityBanner({ missing_required_fields: [] });
    expect(b.tone).toBe("good");
    expect(b.headline).toBe("All required fields were extracted.");
  });

  it("is informational rather than alarming when no report came back", () => {
    const b = toQualityBanner(null);
    expect(b.tone).toBe("info");
    expect(b.missingRequired).toEqual([]);
  });

  it("drops falsy entries rather than rendering blanks", () => {
    const b = toQualityBanner({
      missing_required_fields: ["title", "", null as unknown as string],
      recommendations: ["do a thing", ""],
    });
    expect(b.missingRequired).toEqual(["title"]);
    expect(b.recommendations).toEqual(["do a thing"]);
  });
});

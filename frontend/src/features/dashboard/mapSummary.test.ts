import { describe, expect, it } from "vitest";
import { buildMapSummary } from "./mapSummary";

describe("buildMapSummary", () => {
  it("summarizes local + MoM when MoM is available", () => {
    const s = buildMapSummary({
      local_count: 79,
      mom_count: 3193,
      dropped_no_coords: 0,
      mom_available: true,
    });
    expect(s).toBe("79 OHM facilities · 3,193 Maps of Making spaces");
  });

  it("notes dropped facilities without coordinates", () => {
    const s = buildMapSummary({
      local_count: 2,
      mom_count: 1,
      dropped_no_coords: 3,
      mom_available: true,
    });
    expect(s).toContain("3 without coordinates not shown");
  });

  it("degrades to local-only messaging when MoM is unavailable", () => {
    const s = buildMapSummary({
      local_count: 5,
      mom_count: 0,
      dropped_no_coords: 0,
      mom_available: false,
    });
    expect(s).toContain("Maps of Making unavailable");
    expect(s).not.toContain("Maps of Making spaces");
  });

  it("uses the singular for a single facility", () => {
    const s = buildMapSummary({
      local_count: 1,
      mom_count: 0,
      dropped_no_coords: 0,
      mom_available: false,
    });
    expect(s).toContain("1 OHM facility");
  });
});

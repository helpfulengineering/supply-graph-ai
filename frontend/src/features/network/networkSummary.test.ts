import { describe, expect, it } from "vitest";
import { buildNetworkSummary } from "./networkSummary";

describe("buildNetworkSummary", () => {
  it("summarizes local + MoM when MoM is available", () => {
    expect(
      buildNetworkSummary({ local_count: 79, mom_count: 3193, dropped_no_coords: 0, mom_available: true }),
    ).toBe("79 OHM facilities · 3,193 Maps of Making spaces");
  });

  it("notes dropped facilities without coordinates", () => {
    expect(
      buildNetworkSummary({ local_count: 2, mom_count: 1, dropped_no_coords: 3, mom_available: true }),
    ).toContain("3 without coordinates not shown");
  });

  it("degrades to local-only messaging when MoM is unavailable", () => {
    const s = buildNetworkSummary({ local_count: 5, mom_count: 0, dropped_no_coords: 0, mom_available: false });
    expect(s).toContain("Maps of Making unavailable");
    expect(s).not.toContain("Maps of Making spaces");
  });

  it("uses the singular for a single facility", () => {
    expect(
      buildNetworkSummary({ local_count: 1, mom_count: 0, dropped_no_coords: 0, mom_available: false }),
    ).toContain("1 OHM facility");
  });
});

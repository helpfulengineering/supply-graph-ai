import { describe, expect, it } from "vitest";
import {
  coverageLabel,
  defaultTolerance,
  requirementStats,
  toleranceCeiling,
  withinTolerance,
} from "./nearMiss";

const explanation = (statuses: string[]) => ({
  requirement_matches: statuses.map((status) => ({ status })),
});

describe("requirementStats", () => {
  it("counts total and missing requirements", () => {
    const s = requirementStats(
      explanation(["matched", "matched", "unmatched"]),
    );
    expect(s).toEqual({ total: 3, missing: 1 });
  });

  it("treats any non-matched status as missing", () => {
    const s = requirementStats(explanation(["matched", "partial", "unknown"]));
    expect(s).toEqual({ total: 3, missing: 2 });
  });

  it("returns null when the API gave no structured explanation", () => {
    // Must not be confused with "nothing missing" — that would resurrect the
    // original bug, where non-matches looked like matches.
    expect(requirementStats(null)).toBeNull();
    expect(requirementStats({})).toBeNull();
    expect(requirementStats({ requirement_matches: [] })).toBeNull();
  });
});

describe("toleranceCeiling", () => {
  it("always requires at least two satisfied requirements", () => {
    expect(toleranceCeiling(6)).toBe(4);
    expect(toleranceCeiling(3)).toBe(1);
  });

  it("permits no gap at all for very small designs", () => {
    // With 2 requirements, allowing a gap would mean matching on one process.
    expect(toleranceCeiling(2)).toBe(0);
    expect(toleranceCeiling(1)).toBe(0);
    expect(toleranceCeiling(0)).toBe(0);
  });
});

describe("defaultTolerance", () => {
  it("defaults to a single easy-to-fill gap", () => {
    expect(defaultTolerance(6)).toBe(1);
    expect(defaultTolerance(3)).toBe(1);
  });

  it("never exceeds the ceiling", () => {
    expect(defaultTolerance(2)).toBe(0);
    expect(defaultTolerance(1)).toBe(0);
  });

  it("is always a valid slider position", () => {
    for (let r = 0; r <= 12; r++) {
      expect(defaultTolerance(r)).toBeLessThanOrEqual(toleranceCeiling(r));
      expect(defaultTolerance(r)).toBeGreaterThanOrEqual(0);
    }
  });
});

describe("withinTolerance", () => {
  it("includes exact matches at every setting", () => {
    expect(withinTolerance({ total: 5, missing: 0 }, 0)).toBe(true);
  });

  it("excludes results beyond the chosen tolerance", () => {
    expect(withinTolerance({ total: 5, missing: 2 }, 1)).toBe(false);
    expect(withinTolerance({ total: 5, missing: 2 }, 2)).toBe(true);
  });

  it("shows results with unknown coverage rather than hiding them", () => {
    expect(withinTolerance(null, 0)).toBe(true);
  });
});

describe("coverageLabel", () => {
  it("never reports a bare percentage", () => {
    const label = coverageLabel({ total: 3, missing: 1 });
    expect(label).toBe("Missing 1 of 3 requirements");
    expect(label).not.toMatch(/%/);
  });

  it("states plainly when everything is met", () => {
    expect(coverageLabel({ total: 3, missing: 0 })).toBe(
      "Meets every requirement",
    );
  });

  it("is explicit when coverage is unknown", () => {
    expect(coverageLabel(null)).toBe("Coverage unknown");
  });
});

// The API extracts the same process twice when a design declares it in both
// `manufacturing_processes` and `manufacturing_specs.process_requirements` —
// which is every catalogue design that has both. A three-requirement design
// reported six, and the tolerance slider offered to relax to four.
describe("requirementStats deduplicates requirements", () => {
  const dup = (value: string, status: string) => ({
    requirement_value: value,
    status,
  });

  it("counts a process declared in both sources once", () => {
    const stats = requirementStats({
      requirement_matches: [
        dup("3D Printing", "matched"),
        dup("Laser Cutting", "matched"),
        dup("Assembly", "matched"),
        dup("3D Printing", "matched"),
        dup("Laser Cutting", "matched"),
        dup("Assembly", "matched"),
      ],
    });
    expect(stats).toEqual({ total: 3, missing: 0 });
  });

  it("treats a requirement as missing if any copy is unmatched", () => {
    // Deduping must never hide a gap.
    const stats = requirementStats({
      requirement_matches: [
        dup("Soldering", "matched"),
        dup("Soldering", "not_matched"),
      ],
    });
    expect(stats).toEqual({ total: 1, missing: 1 });
  });

  it("is case- and whitespace-insensitive", () => {
    const stats = requirementStats({
      requirement_matches: [
        dup("3D Printing", "matched"),
        dup(" 3d printing ", "matched"),
      ],
    });
    expect(stats).toEqual({ total: 1, missing: 0 });
  });

  it("keeps unlabelled requirements distinct", () => {
    // Without a value there is nothing to dedupe on; collapsing them would
    // under-count real requirements.
    const stats = requirementStats({
      requirement_matches: [{ status: "matched" }, { status: "not_matched" }],
    });
    expect(stats).toEqual({ total: 2, missing: 1 });
  });

  it("still returns null when the API sent no explanation", () => {
    expect(requirementStats(null)).toBeNull();
    expect(requirementStats({ requirement_matches: [] })).toBeNull();
  });
});

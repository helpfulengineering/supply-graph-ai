import { describe, expect, it } from "vitest";
import { filterByName, matchesName, normalizeForSearch } from "./nameSearch";

const space = (name: string, city?: string, country?: string) => ({
  name,
  city: city ?? null,
  country: country ?? null,
});

const SPACES = [
  space("FabLab Lyon — Association", "Lyon", "France"),
  space("Fablab Coh@bit IUT Bordeaux", "Bordeaux", "France"),
  space("Maker Hanoi", "Hanoi", "Vietnam"),
  space("USC Maker Space", "Los Angeles", "United States"),
  space("Métalab", "Québec", "Canada"),
];

describe("normalizeForSearch", () => {
  it("strips accents, case, and punctuation", () => {
    expect(normalizeForSearch("Métalab")).toBe("metalab");
    expect(normalizeForSearch("Coh@bit")).toBe("coh bit");
    expect(normalizeForSearch("  FabLab—Lyon  ")).toBe("fablab lyon");
  });
});

describe("matchesName", () => {
  it("matches a plain substring", () => {
    expect(matchesName(SPACES[0], "fablab")).toBe(true);
  });

  it("ignores word order", () => {
    // People type what they remember, not what the record says.
    expect(matchesName(SPACES[1], "bordeaux fablab")).toBe(true);
  });

  it("matches on city even when the name omits it", () => {
    expect(matchesName(SPACES[3], "los angeles")).toBe(true);
  });

  it("matches accented names typed without accents", () => {
    expect(matchesName(SPACES[4], "metalab")).toBe(true);
  });

  it("survives punctuation in the record", () => {
    expect(matchesName(SPACES[1], "cohabit")).toBe(false); // 'coh@bit' -> 'coh bit'
    expect(matchesName(SPACES[1], "coh bit")).toBe(true);
  });

  it("requires every term to match", () => {
    expect(matchesName(SPACES[0], "fablab hanoi")).toBe(false);
  });

  it("treats an empty query as matching everything", () => {
    expect(matchesName(SPACES[0], "   ")).toBe(true);
  });
});

describe("filterByName", () => {
  it("returns the original list for an empty query", () => {
    expect(filterByName(SPACES, "")).toHaveLength(SPACES.length);
  });

  it("narrows to the matching spaces", () => {
    const names = filterByName(SPACES, "maker").map((s) => s.name);
    expect(names).toEqual(["Maker Hanoi", "USC Maker Space"]);
  });

  it("returns nothing when there is no match, rather than everything", () => {
    // Silently falling back to the full list would be worse than an empty
    // result: the user would believe their search matched.
    expect(filterByName(SPACES, "nonexistent workshop")).toEqual([]);
  });
});

import { describe, expect, it } from "vitest";
import {
  DEFAULT_DOMAIN,
  navItemsForDomain,
  parseDomain,
} from "./domainPreference";

describe("parseDomain", () => {
  it("defaults to manufacturing for null/empty/invalid", () => {
    expect(DEFAULT_DOMAIN).toBe("manufacturing");
    expect(parseDomain(null)).toBe("manufacturing");
    expect(parseDomain("")).toBe("manufacturing");
    expect(parseDomain("unknown")).toBe("manufacturing");
  });

  it("accepts manufacturing and cooking", () => {
    expect(parseDomain("manufacturing")).toBe("manufacturing");
    expect(parseDomain("cooking")).toBe("cooking");
  });
});

describe("navItemsForDomain", () => {
  it("manufacturing shows Designs, Facilities, Packages, Match", () => {
    expect(navItemsForDomain("manufacturing").map((i) => i.label)).toEqual([
      "Designs",
      "Facilities",
      "Packages",
      "Match",
    ]);
  });

  it("cooking shows only Recipes and Kitchens", () => {
    const items = navItemsForDomain("cooking");
    expect(items.map((i) => i.label)).toEqual(["Recipes", "Kitchens"]);
    expect(items.map((i) => i.to)).toEqual(["/okh", "/facilities"]);
  });
});

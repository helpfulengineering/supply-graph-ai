import { describe, expect, it } from "vitest";
import {
  filtersFromParams,
  filtersToSearch,
  sameFilters,
} from "./filterParams";

describe("filtersFromParams", () => {
  it("reads the filter axes a dashboard link can carry", () => {
    const filters = filtersFromParams(
      new URLSearchParams("country=Germany&process=cnc_machining"),
    );
    expect(filters).toEqual({ country: "Germany", process: "cnc_machining" });
  });

  it("ignores unrelated params, blanks, and an unknown source", () => {
    const filters = filtersFromParams(
      new URLSearchParams("page=3&city=%20%20&source=elsewhere"),
    );
    expect(filters).toEqual({});
  });

  it("keeps a known source", () => {
    expect(filtersFromParams(new URLSearchParams("source=mom"))).toEqual({
      source: "mom",
    });
  });
});

describe("filtersToSearch", () => {
  it("round-trips a filter set", () => {
    const filters = { country: "United States", access_type: "Restricted" };
    expect(
      filtersFromParams(new URLSearchParams(filtersToSearch(filters))),
    ).toEqual(filters);
  });

  it("is empty when nothing is filtered", () => {
    expect(filtersToSearch({})).toBe("");
  });
});

describe("sameFilters", () => {
  it("treats a fresh object with the same axes as unchanged", () => {
    const params = new URLSearchParams("country=Germany&source=mom");
    // Two separate reads of one address: different objects, same filter set.
    expect(
      sameFilters(filtersFromParams(params), filtersFromParams(params)),
    ).toBe(true);
  });

  it("ignores keys the filter set does not own", () => {
    expect(
      sameFilters(
        filtersFromParams(new URLSearchParams("country=Germany&page=2")),
        filtersFromParams(new URLSearchParams("country=Germany&view=map")),
      ),
    ).toBe(true);
  });

  it("sees a changed axis", () => {
    expect(sameFilters({ source: "local" }, { source: "mom" })).toBe(false);
  });

  it("sees an axis that was added or cleared", () => {
    expect(sameFilters({}, { country: "Germany" })).toBe(false);
    expect(sameFilters({ country: "Germany" }, {})).toBe(false);
  });
});

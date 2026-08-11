import { describe, expect, it } from "vitest";
import { filtersFromParams, filtersToSearch } from "./filterParams";

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
    expect(filtersFromParams(new URLSearchParams(filtersToSearch(filters)))).toEqual(
      filters,
    );
  });

  it("is empty when nothing is filtered", () => {
    expect(filtersToSearch({})).toBe("");
  });
});

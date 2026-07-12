import { describe, expect, it } from "vitest";
import {
  countryMatchKey,
  displayCountryName,
  displayRegionName,
  regionMatchKey,
} from "./geoDisplay";

describe("geoDisplay", () => {
  it("shows full country names for ISO codes", () => {
    expect(displayCountryName("US")).toBe("United States");
    expect(displayCountryName("FR")).toBe("France");
    expect(displayCountryName("United States")).toBe("United States");
  });

  it("shows full US state names for abbreviations", () => {
    expect(displayRegionName("TX")).toBe("Texas");
    expect(displayRegionName("Texas")).toBe("Texas");
    expect(displayRegionName("Lazio")).toBe("Lazio");
  });

  it("matches countries by code or full name", () => {
    expect(countryMatchKey("US")).toBe(countryMatchKey("United States"));
    expect(countryMatchKey("FR")).toBe(countryMatchKey("France"));
  });

  it("matches states by abbreviation or full name", () => {
    expect(regionMatchKey("TX")).toBe(regionMatchKey("Texas"));
  });
});

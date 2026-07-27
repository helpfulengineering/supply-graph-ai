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

describe("country names cover the whole ISO range, not a curated table", () => {
  // Codes taken from the live network, which holds 140 distinct country values
  // — 96 of them codes. The old hand-maintained table covered ~46, so the rest
  // rendered raw and dropdowns showed a mix of "France" and "BJ".
  const LIVE_CODES = [
    "AF", "AL", "AM", "AO", "AW", "BA", "BD", "BF", "BG", "BH", "BJ", "BO",
    "BT", "BY", "CD", "CG", "CI", "CM", "CR", "CY", "DJ", "DZ", "EC", "EG", "ET",
  ];

  it("resolves every code to a full name", () => {
    for (const code of LIVE_CODES) {
      const name = displayCountryName(code);
      expect(name, `${code} should resolve to a name`).not.toBe(code);
      expect(name.length).toBeGreaterThan(2);
    }
  });

  it("still honours curated overrides for non-ISO spellings", () => {
    expect(displayCountryName("USA")).toBe("United States");
    expect(displayCountryName("US")).toBe("United States");
  });

  it("collapses a code and its full name to one filter option", () => {
    expect(countryMatchKey("BJ")).toBe(countryMatchKey("Benin"));
    expect(countryMatchKey("FR")).toBe(countryMatchKey("France"));
  });

  it("passes through values that are not country codes", () => {
    expect(displayCountryName("Notacountry")).toBe("Notacountry");
    expect(displayCountryName("")).toBe("");
  });
});

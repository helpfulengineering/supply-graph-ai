import { describe, expect, it } from "vitest";
import { normalizeCityName, normalizedCityOptions } from "./cityNames";

// Every value below is real, taken from the live network's 2,021 distinct city
// values. The false-positive cases matter most: dropping a legitimate city
// hides real facilities, which is worse than showing one odd entry.

describe("drops values that are not city names", () => {
  it.each(["-", "--", "-- .", "107-0052"])("drops %j", (raw) => {
    expect(normalizeCityName(raw)).toBeNull();
  });

  it.each([
    "134 Avenue du Général Leclerc",
    "Apenrader Str. 49",
    "Neckarauer Straße 106-116",
    "Palackého třída 742/82",
    "7 Place Louis Chazette 69001 Lyon",
    "Room 201 & 203 (2nd Floor) , 60 Avenue Victor Hugo , L-1750 Luxemburg",
  ])("drops the street address %j", (raw) => {
    expect(normalizeCityName(raw)).toBeNull();
  });

  it("drops an address even when its house number looks like a postal code", () => {
    // Regression: stripping "134 " first left "Avenue du Général Leclerc",
    // which no longer had a digit for the address check to catch.
    expect(normalizeCityName("134 Avenue du Général Leclerc")).toBeNull();
  });

  it("drops empty and whitespace input", () => {
    expect(normalizeCityName("")).toBeNull();
    expect(normalizeCityName("   ")).toBeNull();
    expect(normalizeCityName(null)).toBeNull();
  });
});

describe("cleans up recoverable values", () => {
  it.each([
    ["1050 Wien", "Wien"],
    ["4040 Linz", "Linz"],
    ["9403 Goldach", "Goldach"],
    ["114 28 Stockholm", "Stockholm"], // Swedish two-group postal code
    ["212 18 Malmö", "Malmö"],
    ["9000 St.Gallen", "St.Gallen"], // "St." is Saint, not Street
  ])("strips the postal code from %j", (raw, want) => {
    expect(normalizeCityName(raw)).toBe(want);
  });

  it("unwraps a fully parenthesised name", () => {
    expect(normalizeCityName("(Incheon)")).toBe("Incheon");
  });

  it("strips a leading slash", () => {
    expect(normalizeCityName("/Stavropol'")).toBe("Stavropol'");
  });
});

describe("leaves legitimate names alone", () => {
  it.each([
    "'s-Hertogenbosch", // leading apostrophe is part of the name
    "Halle (Saale)", // internal parens are the actual name
    "Kempten (Allgäu)",
    "Biel/Bienne", // bilingual name, not a separator
    "Schwedt/Oder",
    "Böblingen/Sindelfingen",
    "ST BENOIT DE CARMAUX", // "ST" is Saint
    "Aarhus N",
    "A Coruna",
    "Sheepscar Street South", // street word, but no number
    "Abidjan, Bingerville",
  ])("keeps %j unchanged", (raw) => {
    expect(normalizeCityName(raw)).toBe(raw);
  });
});

describe("normalizedCityOptions", () => {
  it("collapses variants that normalise to the same name", () => {
    const options = normalizedCityOptions([
      "1050 Wien",
      "1070 Wien",
      "1220 Wien",
      "Wien",
    ]);
    expect(options).toEqual(["Wien"]);
  });

  it("sorts and removes the unusable entries", () => {
    const options = normalizedCityOptions(["Zürich", "-", "Aachen", "107-0052"]);
    expect(options).toEqual(["Aachen", "Zürich"]);
  });

  it("is case-insensitive when deduping but keeps the first spelling", () => {
    expect(normalizedCityOptions(["Berlin", "berlin", "BERLIN"])).toEqual(["Berlin"]);
  });

  it("handles an empty input", () => {
    expect(normalizedCityOptions([])).toEqual([]);
  });
});

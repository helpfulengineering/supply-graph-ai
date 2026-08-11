import { describe, expect, it } from "vitest";
import { hueOf, tileFilter } from "./tileFilter";

/**
 * The property under test is not a particular filter string — those are tuning
 * numbers — but that the map's ground is DERIVED from the world rather than
 * written down, which is the whole defect: one fixed `hue-rotate(180deg)` gave
 * all twenty worlds the same teal map and gave the light ones nothing.
 */

describe("hueOf", () => {
  it("reads a hue from the formats getComputedStyle returns", () => {
    expect(hueOf("rgb(255, 0, 0)")).toBeCloseTo(0);
    expect(hueOf("rgb(0, 255, 0)")).toBeCloseTo(120);
    expect(hueOf("rgb(0, 0, 255)")).toBeCloseTo(240);
  });

  it("calls a grey hueless rather than inventing a colour for it", () => {
    // Mono and Terminal ground on near-neutrals. Rotating toward whatever hue
    // fell out of the rounding would paint a world a colour it never chose.
    expect(hueOf("rgb(18, 18, 18)")).toBeNull();
    expect(hueOf("rgb(250, 250, 250)")).toBeNull();
    expect(hueOf("rgb(128, 130, 129)")).toBeNull();
  });

  it("reads hex, which is how tokens.css actually writes colour", () => {
    // The bug this pins: a custom property is handed back as the literal text
    // of its declaration, not resolved to rgb(). Reading --ttm-accent-cta gets
    // "#38bdf8", and an rgb-only parser finds two numbers in that and gives
    // up — so every world fell back to the grey map this file exists to
    // replace, and nothing looked wrong because grey is a valid answer.
    expect(hueOf("#38bdf8")).toBeCloseTo(hueOf("rgb(56, 189, 248)") ?? -1, 5);
    expect(hueOf("#f00")).toBeCloseTo(0);
    expect(hueOf("#FF0000")).toBeCloseTo(0);
  });

  it("returns null for something that is not a colour", () => {
    expect(hueOf("")).toBeNull();
    expect(hueOf("var(--ttm-pink)")).toBeNull();
  });
});

describe("tileFilter", () => {
  it("inverts only in a dark world, so light tiles are not darkened twice", () => {
    expect(tileFilter({ accent: "rgb(15, 11, 8)", isDark: true })).toContain(
      "invert(1)",
    );
    expect(
      tileFilter({ accent: "rgb(250, 247, 242)", isDark: false }),
    ).not.toContain("invert(1)");
  });

  it("gives two different worlds two different rotations", () => {
    // The regression that motivated this: a constant rotation meant Warm and
    // Ocean drew the same map.
    const warm = tileFilter({ accent: "rgb(250, 247, 242)", isDark: false });
    const ocean = tileFilter({ accent: "rgb(240, 249, 255)", isDark: false });
    expect(warm).not.toBe(ocean);
  });

  it("always flattens OSM's own palette before tinting", () => {
    // Without this the world's hue lands on top of OSM's greens and blues
    // rather than replacing them, and the map reads as two palettes at once.
    for (const isDark of [true, false]) {
      const filter = tileFilter({ accent: "rgb(250, 247, 242)", isDark });
      expect(filter.indexOf("grayscale(1)")).toBeLessThan(
        filter.indexOf("sepia(1)"),
      );
    }
  });

  it("leaves a neutral world neutral", () => {
    const filter = tileFilter({ accent: "rgb(10, 10, 10)", isDark: true });
    expect(filter).toContain("grayscale(1)");
    expect(filter).not.toContain("sepia");
    expect(filter).not.toContain("hue-rotate");
  });

  it("emits a filter CSS can parse", () => {
    // A malformed step silently voids the WHOLE filter — the map would render
    // raw OSM tiles and nothing would say why.
    const filter = tileFilter({ accent: "rgb(255, 0, 0)", isDark: false });
    expect(filter).toMatch(/^([a-z-]+\([^)]*\)\s?)+$/);
    expect(filter).not.toMatch(/NaN|undefined|null/);
  });
});

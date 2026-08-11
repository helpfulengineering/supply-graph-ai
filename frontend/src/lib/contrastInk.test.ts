import { describe, expect, it } from "vitest";
import {
  AA_NORMAL,
  contrastRatio,
  inkFor,
  mix,
  parseRgb,
  formatRgb,
} from "./contrastInk";

const WHITE = { r: 255, g: 255, b: 255 };
const BLACK = { r: 0, g: 0, b: 0 };

describe("contrastRatio", () => {
  it("is 21 for black on white", () => {
    expect(contrastRatio(BLACK, WHITE)).toBeCloseTo(21, 5);
  });

  it("is 1 for a colour against itself", () => {
    expect(contrastRatio(WHITE, WHITE)).toBeCloseTo(1, 5);
  });

  it("does not care which way round the pair is given", () => {
    const pink = { r: 249, g: 168, b: 212 };
    expect(contrastRatio(pink, BLACK)).toBeCloseTo(contrastRatio(BLACK, pink), 9);
  });
});

describe("parseRgb", () => {
  it("reads what a computed style hands back", () => {
    expect(parseRgb("rgb(34, 16, 26)")).toEqual({ r: 34, g: 16, b: 26 });
    expect(parseRgb("rgba(1, 2, 3, 0.5)")).toEqual({ r: 1, g: 2, b: 3 });
  });

  it("returns null for anything else", () => {
    expect(parseRgb("transparent")).toBeNull();
  });
});

describe("mix", () => {
  it("returns each end at the extremes", () => {
    expect(mix(BLACK, WHITE, 1)).toEqual(BLACK);
    expect(mix(BLACK, WHITE, 0)).toEqual(WHITE);
  });

  it("meets in the middle", () => {
    expect(formatRgb(mix(BLACK, WHITE, 0.5))).toBe("rgb(128, 128, 128)");
  });
});

describe("inkFor", () => {
  it("leaves an accent that already reads undiluted", () => {
    const strong = { r: 128, g: 0, b: 0 };
    expect(inkFor(strong, BLACK, WHITE)).toEqual(strong);
  });

  it("clears AA for a pale accent on a light surface", () => {
    // The reported defect: Mono's grey and Bubblegum's pink in light mode.
    for (const pale of [
      { r: 200, g: 200, b: 200 },
      { r: 249, g: 168, b: 212 },
    ]) {
      const ink = inkFor(pale, BLACK, WHITE);
      expect(contrastRatio(ink, WHITE)).toBeGreaterThanOrEqual(AA_NORMAL);
    }
  });

  it("clears AA for a dark accent on a dark surface", () => {
    const ink = inkFor({ r: 40, g: 20, b: 60 }, WHITE, { r: 34, g: 16, b: 26 });
    expect(contrastRatio(ink, { r: 34, g: 16, b: 26 })).toBeGreaterThanOrEqual(
      AA_NORMAL,
    );
  });

  it("keeps as much of the accent as the ratio allows", () => {
    const pale = { r: 249, g: 168, b: 212 };
    const ink = inkFor(pale, BLACK, WHITE);
    // Corrected, but not collapsed to the body text colour.
    expect(ink).not.toEqual(BLACK);
    expect(ink.r).toBeGreaterThan(ink.g);
  });

  it("falls back to the body text when no blend can clear the target", () => {
    // An impossible target: nothing reaches 21:1 on a mid grey.
    const grey = { r: 128, g: 128, b: 128 };
    expect(inkFor(WHITE, BLACK, grey, 21)).toEqual(BLACK);
  });
});

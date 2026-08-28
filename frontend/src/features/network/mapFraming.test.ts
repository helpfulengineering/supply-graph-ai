import { describe, expect, it } from "vitest";
import { denseBounds, fillZoom, fitPadding } from "./mapFraming";

function space(lat: number, lon: number) {
  return { lat, lon };
}

describe("fillZoom", () => {
  it("is the zoom where one world covers the container", () => {
    // 256px world at zoom 0, doubling each step.
    expect(fillZoom(256, 256)).toBe(0);
    expect(fillZoom(512, 512)).toBe(1);
    expect(fillZoom(1024, 1024)).toBe(2);
  });

  it("measures the narrower side, whichever it is", () => {
    expect(fillZoom(360, 400)).toBe(fillZoom(400, 360));
  });

  it("leaves a wide dashboard panel able to frame the whole world", () => {
    // 1215x438: measured by width the floor is 3 and the full extent, which
    // fits at 2, becomes unreachable on the one surface that exists to show it.
    expect(fillZoom(1215, 438)).toBeLessThanOrEqual(2);
  });

  it("never goes negative for a container smaller than one tile", () => {
    expect(fillZoom(120, 90)).toBe(0);
  });

  it("floors a phone panel above the whole-world fit a desktop gets", () => {
    // The bug: a worldwide network fitted on a phone lands at zoom 0.
    expect(fillZoom(360, 440)).toBeGreaterThan(0);
  });
});

describe("denseBounds", () => {
  it("frames the busiest neighbourhood, not the far-flung few", () => {
    const spaces = [
      ...Array.from({ length: 18 }, () => space(48, 2)),
      space(-41, 174),
      space(-33, -70),
    ];
    expect(denseBounds(spaces)).toEqual([
      [48, 2],
      [48, 2],
    ]);
  });

  it("centres on a place when the set is bimodal", () => {
    // The failure the percentile trim had: half in Europe, fewer in the
    // Americas, and the midpoint of the two is open ocean.
    const spaces = [
      ...Array.from({ length: 20 }, (_, i) => space(48 + i * 0.1, 2 + i * 0.1)),
      ...Array.from({ length: 8 }, (_, i) => space(40 + i * 0.1, -74 + i * 0.1)),
    ];
    const [[south, west], [north, east]] = denseBounds(spaces);
    expect(west).toBeGreaterThan(0);
    expect(east).toBeLessThan(20);
    expect(south).toBeGreaterThan(40);
    expect(north).toBeLessThan(60);
  });

  it("includes the neighbouring cells, so a border does not split a region", () => {
    // 9.9 and 10.1 straddle a 10-degree cell edge; both belong to the frame.
    const spaces = [space(9.9, 0), space(9.9, 0), space(10.1, 0)];
    expect(denseBounds(spaces)).toEqual([
      [9.9, 0],
      [10.1, 0],
    ]);
  });

  it("survives a single space", () => {
    expect(denseBounds([space(51.5, -0.1)])).toEqual([
      [51.5, -0.1],
      [51.5, -0.1],
    ]);
  });
});

describe("fitPadding", () => {
  it("caps at the desktop inset", () => {
    expect(fitPadding(1200, 520)).toBe(30);
  });

  it("shrinks with the container so a phone keeps its screen", () => {
    expect(fitPadding(360, 440)).toBeLessThan(30);
  });
});

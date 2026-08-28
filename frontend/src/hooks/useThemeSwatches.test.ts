import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { resolveThemeSwatches } from "./useThemeSwatches";
import { THEMES } from "./useDarkMode";

/**
 * The resolver flips `data-ttm-theme` on <html> to read each world's tokens.
 * jsdom does not implement the cascade, so these assert the MECHANISM — that
 * every world is visited and, above all, that the document is left exactly as
 * it was found. The colour values themselves are asserted against the real
 * cascade in e2e/themes.spec.ts, which is the only place they mean anything.
 */
describe("resolveThemeSwatches", () => {
  const root = document.documentElement;

  beforeEach(() => {
    root.removeAttribute("data-ttm-theme");
    vi.restoreAllMocks();
  });
  afterEach(() => {
    root.removeAttribute("data-ttm-theme");
  });

  it("returns an entry for every declared world", () => {
    const out = resolveThemeSwatches();
    expect(Object.keys(out).sort()).toEqual(THEMES.map((t) => t.slug).sort());
  });

  it("visits each world exactly once", () => {
    const seen: string[] = [];
    const original = root.setAttribute.bind(root);
    vi.spyOn(root, "setAttribute").mockImplementation((name, value) => {
      if (name === "data-ttm-theme") seen.push(value);
      original(name, value);
    });
    resolveThemeSwatches();
    expect(seen).toEqual(THEMES.map((t) => t.slug));
  });

  it("restores the world that was active before it ran", () => {
    root.setAttribute("data-ttm-theme", "ocean");
    resolveThemeSwatches();
    expect(root.getAttribute("data-ttm-theme")).toBe("ocean");
  });

  it("leaves no attribute behind when none was set", () => {
    // The default world is the absence of the attribute (Warm applies on bare
    // :root). Writing "ttm" back would be a different thing than what it found.
    resolveThemeSwatches();
    expect(root.hasAttribute("data-ttm-theme")).toBe(false);
  });

  it("restores the original world even if reading throws", () => {
    // Without the finally, a throw mid-loop strands the whole app in whichever
    // world the loop had reached — a cosmetic bug that outlives the error.
    root.setAttribute("data-ttm-theme", "forest");
    vi.spyOn(window, "getComputedStyle").mockImplementation(() => {
      throw new Error("boom");
    });
    expect(() => resolveThemeSwatches()).toThrow("boom");
    expect(root.getAttribute("data-ttm-theme")).toBe("forest");
  });
});

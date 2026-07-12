import { describe, expect, it } from "vitest";
import { normalizeHardwareLicense } from "./normalizeHardwareLicense";

describe("normalizeHardwareLicense", () => {
  it("collapses CERN-OHL P/S/W variants", () => {
    expect(normalizeHardwareLicense("CERN-OHL-P-2.0")).toBe("CERN-OHL-2.0");
    expect(normalizeHardwareLicense("CERN-OHL-S-2.0")).toBe("CERN-OHL-2.0");
    expect(normalizeHardwareLicense("CERN-OHL-W-2.0")).toBe("CERN-OHL-2.0");
  });

  it("collapses AGPL/GPL only and or-later variants", () => {
    expect(normalizeHardwareLicense("AGPL-3.0")).toBe("AGPL-3.0");
    expect(normalizeHardwareLicense("AGPL-3.0-only")).toBe("AGPL-3.0");
    expect(normalizeHardwareLicense("AGPL-3.0-or-later")).toBe("AGPL-3.0");
    expect(normalizeHardwareLicense("GPL-3.0-only")).toBe("GPL-3.0");
  });

  it("leaves unrelated licenses alone", () => {
    expect(normalizeHardwareLicense("MIT")).toBe("MIT");
    expect(normalizeHardwareLicense("CC-BY-4.0")).toBe("CC-BY-4.0");
  });

  it("handles empty", () => {
    expect(normalizeHardwareLicense(null)).toBeNull();
    expect(normalizeHardwareLicense("  ")).toBeNull();
  });
});

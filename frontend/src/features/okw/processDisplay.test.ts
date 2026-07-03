import { describe, expect, it } from "vitest";
import { humanizeProcess } from "./processDisplay";

describe("humanizeProcess", () => {
  it("humanizes a Wikipedia URI to a readable label", () => {
    expect(humanizeProcess("https://en.wikipedia.org/wiki/Laser_cutter")).toBe(
      "Laser Cutter",
    );
    expect(humanizeProcess("https://en.wikipedia.org/wiki/Assembly_station")).toBe(
      "Assembly Station",
    );
  });

  it("leaves a plain name unchanged", () => {
    expect(humanizeProcess("Laser Cutting")).toBe("Laser Cutting");
  });
});

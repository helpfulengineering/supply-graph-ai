import { describe, expect, it } from "vitest";
import { deriveFilterOptions, humanizeProcessId } from "./deriveFilterOptions";
import type { NetworkSpace } from "../../api/ohm/network";

function space(p: Partial<NetworkSpace>): NetworkSpace {
  return {
    id: "x", name: "X", lat: 0, lon: 0, source: "local", city: null, region: null,
    country: null, status: null, processes: [], access_type: null, url: null, ...p,
  };
}

describe("humanizeProcessId", () => {
  it("title-cases a canonical process id", () => {
    expect(humanizeProcessId("laser_cutting")).toBe("Laser Cutting");
    expect(humanizeProcessId("cnc_machining")).toBe("Cnc Machining");
  });
});

describe("deriveFilterOptions", () => {
  it("derives distinct, sorted options across spaces", () => {
    const spaces = [
      space({ country: "US", region: "TX", status: "active", access_type: "Public", processes: ["laser_cutting"] }),
      space({ country: "IT", region: null, status: "active", access_type: null, processes: ["cnc_machining", "laser_cutting"], source: "mom" }),
    ];
    const o = deriveFilterOptions(spaces);
    expect(o.countries).toEqual(["IT", "US"]);
    expect(o.regions).toEqual(["TX"]);
    expect(o.statuses).toEqual(["active"]);
    expect(o.accessTypes).toEqual(["Public"]);
    expect(o.processes.map((p) => p.id)).toEqual(["cnc_machining", "laser_cutting"]);
    expect(o.processes.find((p) => p.id === "laser_cutting")?.label).toBe("Laser Cutting");
  });

  it("handles an empty set", () => {
    const o = deriveFilterOptions([]);
    expect(o.countries).toEqual([]);
    expect(o.processes).toEqual([]);
  });
});

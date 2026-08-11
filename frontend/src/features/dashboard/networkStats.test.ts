import { describe, expect, it } from "vitest";
import type { NetworkSpace } from "../../api/ohm/network";
import {
  capabilityCoverage,
  facilitiesByCountry,
  spacesBySource,
} from "./networkStats";

function space(overrides: Partial<NetworkSpace> = {}): NetworkSpace {
  return {
    id: "1",
    name: "Space",
    lat: 0,
    lon: 0,
    source: "local",
    city: null,
    region: null,
    country: "Germany",
    status: null,
    processes: [],
    access_type: null,
    url: null,
    ...overrides,
  };
}

describe("facilitiesByCountry", () => {
  it("counts by country, largest first, keyed by the filter value", () => {
    const rows = facilitiesByCountry([
      space({ country: "Germany" }),
      space({ country: "Germany" }),
      space({ country: "France" }),
      space({ country: null }),
    ]);
    expect(rows).toEqual([
      { key: "Germany", label: "Germany", value: 2 },
      { key: "France", label: "France", value: 1 },
    ]);
  });

  it("keeps every country unless a limit is asked for", () => {
    const spaces = [
      space({ country: "A" }),
      space({ country: "B" }),
      space({ country: "C" }),
    ];
    expect(facilitiesByCountry(spaces)).toHaveLength(3);
    expect(facilitiesByCountry(spaces, 1)).toHaveLength(1);
  });
});

describe("capabilityCoverage", () => {
  it("reads the slug in words but keeps it as the key", () => {
    const rows = capabilityCoverage([
      space({ processes: ["cnc_machining", "3d_printing"] }),
      space({ processes: ["cnc_machining"] }),
    ]);
    expect(rows).toEqual([
      { key: "cnc_machining", label: "cnc machining", value: 2 },
      { key: "3d_printing", label: "3d printing", value: 1 },
    ]);
  });

  it("counts memberships across spaces and skips empties", () => {
    const rows = capabilityCoverage([
      space({ processes: ["sewing", ""] }),
      space({ processes: undefined as unknown as string[] }),
    ]);
    expect(rows).toEqual([{ key: "sewing", label: "sewing", value: 1 }]);
  });
});

describe("spacesBySource", () => {
  it("labels the two sources and keys them by the filter value", () => {
    const rows = spacesBySource([
      space({ source: "local" }),
      space({ source: "mom" }),
      space({ source: "mom" }),
    ]);
    expect(rows).toEqual([
      { key: "mom", label: "Maps of Making", value: 2 },
      { key: "local", label: "OHM facilities", value: 1 },
    ]);
  });
});

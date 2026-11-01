import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { NetworkSpace } from "../../api/ohm/network";
import { NetworkSpaceCard } from "./NetworkSpaceCard";

function space(overrides: Partial<NetworkSpace> = {}): NetworkSpace {
  return {
    id: "okw-1",
    name: "Community Workshop",
    lat: null,
    lon: null,
    city: "Ghent",
    region: null,
    country: "BE",
    source: "local",
    status: null,
    processes: [],
    access_type: null,
    url: null,
    visibility: "private",
    ambiguous: false,
    ...overrides,
  };
}

describe("NetworkSpaceCard visibility (#576)", () => {
  it("badges a local facility with its visibility", () => {
    render(<NetworkSpaceCard space={space({ visibility: "members" })} />);
    expect(screen.getByText("Members")).toBeInTheDocument();
  });

  it("shows no visibility for a Maps of Making space", () => {
    render(
      <NetworkSpaceCard
        space={space({ source: "mom", visibility: null, url: null })}
      />,
    );
    for (const label of ["Private", "Members", "Followers", "Public"]) {
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    }
  });
});

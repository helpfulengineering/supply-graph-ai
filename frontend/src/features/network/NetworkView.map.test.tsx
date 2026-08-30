import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import type { NetworkSpace } from "../../api/ohm/network";
import { NetworkView } from "./NetworkView";

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ hasWrite: true }),
}));

/**
 * The real map needs Leaflet and a laid-out container, neither of which jsdom
 * has. What the list under the map depends on is one contract — the map hands
 * back the spaces it currently frames — so the double is a button that reports
 * a region, which is what panning does.
 */
vi.mock("./NetworkMapLazy", () => ({
  NetworkMap: ({
    spaces,
    onVisibleChange,
  }: {
    spaces: NetworkSpace[];
    onVisibleChange?: (visible: NetworkSpace[]) => void;
  }) => (
    <>
      <button
        type="button"
        onClick={() =>
          onVisibleChange?.(spaces.filter((s) => s.city === "Berlin"))
        }
      >
        pan to Berlin
      </button>
      <button type="button" onClick={() => onVisibleChange?.([])}>
        pan to the ocean
      </button>
    </>
  ),
}));

function space(overrides: Partial<NetworkSpace>): NetworkSpace {
  return {
    id: "s1",
    name: "A space",
    source: "mom",
    lat: 0,
    lon: 0,
    city: null,
    region: null,
    country: null,
    status: null,
    access_type: null,
    url: null,
    ambiguous: false,
    processes: [],
    ...overrides,
  };
}

const SPACES = [
  space({ id: "1", name: "Berlin Offene Werkstatt", city: "Berlin" }),
  space({ id: "2", name: "schokowerkstatt", city: "Berlin" }),
  space({ id: "3", name: "Lisbon Makers", city: "Lisbon" }),
];

function renderNetwork() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <NetworkView />
    </QueryClientProvider>,
  );
}

describe("NetworkView map view", () => {
  beforeEach(() => {
    server.use(
      http.get("*/v1/api/okw/spaces", () =>
        HttpResponse.json({
          success: true,
          spaces: SPACES,
          total: SPACES.length,
          local_count: 0,
          mom_count: SPACES.length,
          dropped_no_coords: 0,
          mom_available: true,
        }),
      ),
    );
  });

  it("lists the spaces the map frames, under the map", async () => {
    const user = userEvent.setup();
    renderNetwork();

    await user.click(await screen.findByRole("radio", { name: "Map" }));
    // Before the map reports, the list is everything the filters returned.
    expect(await screen.findByText("Lisbon Makers")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "pan to Berlin" }));

    await waitFor(() =>
      expect(screen.queryByText("Lisbon Makers")).not.toBeInTheDocument(),
    );
    expect(screen.getByText("Berlin Offene Werkstatt")).toBeInTheDocument();
    expect(screen.getByText("schokowerkstatt")).toBeInTheDocument();
    expect(screen.getByText(/2 spaces in view/)).toBeInTheDocument();
  });

  it("says so when the region holds nothing, and keeps the full list in list view", async () => {
    const user = userEvent.setup();
    renderNetwork();

    await user.click(await screen.findByRole("radio", { name: "Map" }));
    await screen.findByText("Lisbon Makers");
    await user.click(screen.getByRole("button", { name: "pan to the ocean" }));

    expect(await screen.findByText(/No spaces in view/)).toBeInTheDocument();
    expect(
      screen.queryByText("Berlin Offene Werkstatt"),
    ).not.toBeInTheDocument();

    // Leaving the map is leaving the region: the list is the filters again.
    await user.click(screen.getByRole("radio", { name: "List" }));
    expect(screen.getByText("Lisbon Makers")).toBeInTheDocument();
    expect(screen.queryByText(/in view/)).not.toBeInTheDocument();
  });
});

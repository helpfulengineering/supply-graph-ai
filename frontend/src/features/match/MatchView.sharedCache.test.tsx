import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("../../api/ohm/network", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/ohm/network")>();
  return { ...actual, fetchNetworkSpaces: vi.fn() };
});
vi.mock("../../api/ohm/okh", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/ohm/okh")>();
  return { ...actual, fetchAllOkhList: vi.fn() };
});

import { MatchView } from "./MatchView";
import { fetchNetworkSpaces } from "../../api/ohm/network";
import { fetchAllOkhList } from "../../api/ohm/okh";
import type { NetworkData } from "../../api/ohm/network";

const seededNetwork: NetworkData = {
  spaces: [
    {
      id: "space-1",
      name: "Alpha Lab",
      lat: 45.5,
      lon: -122.6,
      source: "local",
      city: "Portland",
      region: "OR",
      country: "US",
      status: null,
      processes: [],
      access_type: null,
      url: null,
    },
  ],
  total: 1,
  local_count: 1,
  mom_count: 0,
  dropped_no_coords: 0,
  mom_available: false,
};

describe("MatchView network cache sharing", () => {
  it("reads facilities from the shared [network, baseline] cache without refetching", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { staleTime: Infinity, retry: false } },
    });
    // Pre-populate the SAME key the Home and Network pages use. If MatchView
    // used a different key, it would miss this cache and call the fetcher.
    client.setQueryData(["network", "baseline"], seededNetwork);
    client.setQueryData(["okh-list"], {
      items: [],
      pagination: {
        page: 1,
        page_size: 0,
        total_items: 0,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
    });

    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <MatchView />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Alpha Lab")).toBeInTheDocument();
    expect(fetchNetworkSpaces).not.toHaveBeenCalled();
    expect(fetchAllOkhList).not.toHaveBeenCalled();
  });
});

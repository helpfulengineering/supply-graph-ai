import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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
import type { MatchDomain } from "../../api/ohm/match";
import { fetchNetworkSpaces, type NetworkData } from "../../api/ohm/network";
import { fetchAllOkhList } from "../../api/ohm/okh";

/**
 * The domains the API really returns: `id` is the key it matches on, `name` is
 * a human label, and the two are different strings.
 */
const domains: MatchDomain[] = [
  {
    id: "manufacturing",
    name: "Manufacturing & Hardware Production",
    status: "available",
  },
  { id: "cooking", name: "Cooking & Food Preparation", status: "available" },
];

function renderView() {
  const emptyNetwork: NetworkData = {
    spaces: [],
    total: 0,
    local_count: 0,
    mom_count: 0,
    dropped_no_coords: 0,
    mom_available: false,
  };
  vi.mocked(fetchNetworkSpaces).mockResolvedValue(emptyNetwork);
  vi.mocked(fetchAllOkhList).mockResolvedValue({
    items: [],
    pagination: {
      page: 1,
      page_size: 100,
      total_items: 0,
      total_pages: 0,
      has_next: false,
      has_previous: false,
    },
  });

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(["match-domains"], domains);
  return render(
    <QueryClientProvider client={client}>
      <MatchView />
    </QueryClientProvider>,
  );
}

describe("MatchView domain selector", () => {
  it("submits the domain key while showing the display name", async () => {
    renderView();

    const select = (await screen.findByLabelText(/Domain/i)) as HTMLSelectElement;
    const options = Array.from(select.options);

    // The regression: the option value must be the key the API matches on.
    // Binding it to the label sent "Manufacturing & Hardware Production" as
    // `domain` and the server answered "Unsupported domain".
    expect(options.map((o) => o.value)).toEqual([
      "",
      "manufacturing",
      "cooking",
    ]);
    expect(options.map((o) => o.textContent?.trim())).toEqual([
      "Detect automatically",
      "Manufacturing & Hardware Production",
      "Cooking & Food Preparation",
    ]);
  });

  it("keeps an empty value for automatic detection, which the server treats as absent", async () => {
    renderView();
    const select = (await screen.findByLabelText(/Domain/i)) as HTMLSelectElement;
    expect(select.value).toBe("");
  });
});

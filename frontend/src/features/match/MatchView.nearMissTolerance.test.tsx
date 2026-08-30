import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import type { OkhManifest } from "../../types/okh";
import type { NetworkData } from "../../api/ohm/network";
import { MatchView } from "./MatchView";

const design: OkhManifest = {
  id: "design-1",
  title: "Widget",
  version: null,
  repo: null,
  function: null,
  description: null,
  intended_use: null,
  keywords: [],
  documentation_language: null,
  license: null,
  licensor: { name: "Acme" } as OkhManifest["licensor"],
  contributors: [],
  manufacturing_processes: [],
  materials: [],
  design_files: [],
  manufacturing_files: [],
  making_instructions: [],
  parts: [],
  tool_list: [],
  image: null,
  project_link: null,
};

const seededNetwork: NetworkData = {
  spaces: [
    {
      id: "facility-1",
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
      ambiguous: false,
    },
  ],
  total: 1,
  local_count: 1,
  mom_count: 0,
  dropped_no_coords: 0,
  mom_available: false,
};

function renderView() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(["network", "baseline"], seededNetwork);
  client.setQueryData(["okh-list"], {
    items: [design],
    pagination: {
      page: 1,
      page_size: 1,
      total_items: 1,
      total_pages: 1,
      has_next: false,
      has_previous: false,
    },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <MatchView okhId="design-1" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MatchView — near-miss tolerance", () => {
  it("surfaces the tolerance slider instead of a blank empty state when every facility is hidden by default tolerance", async () => {
    // 5 requirements, 3 missing: exceeds the default tolerance of 1, so the
    // one and only solution is hidden by `withinTolerance` — but the API DID
    // return a match, so this must not render the "zero solutions" empty state.
    server.use(
      http.post("*/v1/api/match", () =>
        HttpResponse.json({
          data: {
            solutions: [
              {
                facility_id: "facility-1",
                facility_name: "Alpha Lab",
                confidence: 0.4,
                score: 0.4,
                rank: 1,
                match_type: "manufacturing",
                explanation: {
                  requirement_matches: [
                    { requirement_value: "cnc milling", status: "matched" },
                    { requirement_value: "welding", status: "matched" },
                    { requirement_value: "anodizing", status: "not_matched" },
                    { requirement_value: "laser cutting", status: "not_matched" },
                    { requirement_value: "3d printing", status: "not_matched" },
                  ],
                },
              },
            ],
            total_solutions: 1,
          },
        }),
      ),
    );

    const user = userEvent.setup();
    renderView();

    await user.click(await screen.findByLabelText(/^Alpha Lab\b/));
    await user.click(screen.getByRole("button", { name: "Run Match" }));

    expect(
      await screen.findByLabelText(/Allow facilities missing up to/),
    ).toBeInTheDocument();
    expect(screen.getByText(/1 facility is hidden at this setting/)).toBeInTheDocument();
    expect(screen.queryByText("No matches found")).not.toBeInTheDocument();

    const slider = screen.getByLabelText(/Allow facilities missing up to/) as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "3" } });

    expect(await screen.findByLabelText("Select Alpha Lab")).toBeInTheDocument();
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("../../api/ohm/network", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/ohm/network")>();
  return { ...actual, fetchNetworkSpaces: vi.fn() };
});
vi.mock("../../api/ohm/okh", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/ohm/okh")>();
  return { ...actual, fetchAllOkhList: vi.fn() };
});
vi.mock("../../api/ohm/match", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/ohm/match")>();
  return { ...actual, runMatch: vi.fn() };
});

import { MatchView } from "./MatchView";
import { runMatch } from "../../api/ohm/match";
import { fetchNetworkSpaces } from "../../api/ohm/network";
import { fetchAllOkhList } from "../../api/ohm/okh";

function renderView() {
  vi.mocked(fetchNetworkSpaces).mockResolvedValue({
    spaces: [],
    total: 0,
    local_count: 0,
    mom_count: 0,
    dropped_no_coords: 0,
    mom_available: false,
  });
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
  vi.mocked(runMatch).mockReturnValue(new Promise(() => {}));
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  client.setQueryData(["match-domains"], []);
  return render(
    <QueryClientProvider client={client}>
      <MatchView okhId="design-1" />
    </QueryClientProvider>,
  );
}

describe("MatchView members-only toggle (#575)", () => {
  it("matches against this node's member facilities without picking any", async () => {
    renderView();
    const run = screen.getByRole("button", { name: "Run Match" });
    expect(run).toBeDisabled();

    await userEvent.click(
      screen.getByRole("checkbox", { name: /members' facilities only/i }),
    );

    expect(
      screen.queryByLabelText("Filter facilities by name"),
    ).not.toBeInTheDocument();
    expect(run).toBeEnabled();
    await userEvent.click(run);
    expect(vi.mocked(runMatch).mock.calls[0][0]).toMatchObject({
      okhId: "design-1",
      networkFilter: { include_mom: false, members_only: true },
    });
    expect(vi.mocked(runMatch).mock.calls[0][0].okwIds).toBeUndefined();
  });
});

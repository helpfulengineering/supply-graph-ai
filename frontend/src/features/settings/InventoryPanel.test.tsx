import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { InventoryPanel } from "./InventoryPanel";

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <InventoryPanel />
    </QueryClientProvider>,
  );
}

describe("InventoryPanel", () => {
  it("shows identifiers and metadata, and never content", async () => {
    renderPanel();

    expect(await screen.findByText("okh-0001")).toBeInTheDocument();
    expect(screen.getByText("did:key:zAdaRegistered")).toBeInTheDocument();
    expect(screen.getByText("4 KB")).toBeInTheDocument();

    // Not a browse surface: there is no title column, because a title states
    // intent and intent is most of what a private draft is.
    const table = screen.getByRole("table");
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((h) => h.textContent);
    expect(headers).toEqual(["Id", "Owner", "Visibility", "Size", "Last write"]);
    expect(headers).not.toContain("Title");
  });

  it("says how many records only their owner can see", async () => {
    renderPanel();
    expect(
      await screen.findByText(/2 record\(s\), 1 visible only to their owner/),
    ).toBeInTheDocument();
  });

  it("filters to the records that are not shared", async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText("okh-0001");

    await user.click(
      screen.getByLabelText("Only records nobody else can see"),
    );

    expect(screen.getByText("okh-0001")).toBeInTheDocument();
    expect(screen.queryByText("okh-0002")).not.toBeInTheDocument();
  });

  it("filters by owner across both identifiers", async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText("okh-0001");

    // An account id, for the row that has no DID — the fallback identifier
    // has to be searchable or pre-#403 records are unfindable by owner.
    await user.type(screen.getByLabelText("Owner"), "000000000001");

    expect(screen.getByText("okh-0002")).toBeInTheDocument();
    expect(screen.queryByText("okh-0001")).not.toBeInTheDocument();
  });

  it("distinguishes an empty node from an empty filter", async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText("okh-0001");

    await user.type(screen.getByLabelText("Owner"), "nobody");

    expect(screen.getByText("No records match those filters.")).toBeInTheDocument();
    expect(
      screen.queryByText("This node holds no records yet."),
    ).not.toBeInTheDocument();
  });
});

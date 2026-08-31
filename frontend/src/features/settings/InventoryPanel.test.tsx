import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import { securityPolicyFixture } from "../../test/fixtures";
import { ToastProvider } from "../../components/ui/Toast";
import { InventoryPanel } from "./InventoryPanel";

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <InventoryPanel />
      </ToastProvider>
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

describe("InventoryPanel — break-glass (#406)", () => {
  it("offers no break-glass affordance in peacetime", async () => {
    renderPanel();
    await screen.findByText("okh-0001");

    // Rendering a button that always refuses would teach an operator that the
    // boundary is a formality.
    expect(
      screen.queryByRole("button", { name: "Break glass" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Access")).not.toBeInTheDocument();
  });

  it("offers it in crisis, and only on records nobody else can see", async () => {
    server.use(
      http.get("*/v1/api/identity/security-policy", () =>
        HttpResponse.json({
          ...securityPolicyFixture,
          mode: "crisis",
          admin_break_glass: true,
        }),
      ),
    );
    renderPanel();

    const buttons = await screen.findAllByRole("button", { name: "Break glass" });
    // Two rows in the fixture; only the private one is readable-on-the-record,
    // because the public one an admin can already read like anyone else.
    expect(buttons).toHaveLength(1);
  });

  it("does not call the API when the admin declines to give a reason", async () => {
    const calls: string[] = [];
    server.use(
      http.get("*/v1/api/identity/security-policy", () =>
        HttpResponse.json({
          ...securityPolicyFixture,
          mode: "crisis",
          admin_break_glass: true,
        }),
      ),
      http.post("*/v1/api/okh/:id/break-glass", ({ params }) => {
        calls.push(String(params.id));
        return HttpResponse.json({});
      }),
    );
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue(null);
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole("button", { name: "Break glass" }));

    expect(calls).toEqual([]);
    // The prompt has to say what it costs, or consent to it is not informed.
    expect(promptSpy.mock.calls[0]?.[0]).toMatch(/recorded and shown to the person/);
    promptSpy.mockRestore();
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, beforeEach } from "vitest";
import { server } from "../../test/msw/server";
import { AuthProvider } from "../../context/AuthContext";
import { ToastProvider } from "../../components/ui/Toast";
import { AccountView } from "./AccountView";
import { setToken } from "./tokenStorage";

function renderView() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <AuthProvider>
          <AccountView />
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

/** Answers only `mine=true`, so a view that forgets the filter shows nothing. */
function myDesigns(items: unknown[]) {
  server.use(
    http.get("*/v1/api/okh", ({ request }) => {
      const mine = new URL(request.url).searchParams.get("mine") === "true";
      const rows = mine ? items : [];
      return HttpResponse.json({
        items: rows,
        pagination: {
          page: 1,
          page_size: 100,
          total_items: rows.length,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      });
    }),
  );
}

beforeEach(() => {
  sessionStorage.clear();
});

describe("AccountView", () => {
  it("points an anonymous visitor at registration", async () => {
    renderView();
    expect(await screen.findByText("You are not signed in")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Register" })).toHaveAttribute(
      "href",
      "/register",
    );
  });

  it("lists every design you created, shared or not, with its visibility", async () => {
    setToken("tok");
    myDesigns([
      { id: "d1", title: "Unshared Widget", visibility: "private" },
      { id: "d2", title: "Shared Widget", visibility: "public" },
    ]);
    renderView();

    const designs = await screen.findByRole("region", { name: "Your designs" });
    expect(await screen.findByText("Unshared Widget")).toBeInTheDocument();
    expect(screen.getByText("Shared Widget")).toBeInTheDocument();
    expect(designs).toHaveTextContent("Private");
    expect(designs).toHaveTextContent("Public");
  });

  it("previews the audience, then applies one level to the selected designs", async () => {
    setToken("tok");
    myDesigns([
      { id: "d1", title: "Unshared Widget", visibility: "private" },
      { id: "d2", title: "Shared Widget", visibility: "public" },
    ]);
    let posted: unknown = null;
    server.use(
      http.post("*/v1/api/okh/visibility", async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json({
          results: [
            { id: "d1", outcome: "changed", visibility: "members" },
            { id: "d2", outcome: "not_yours" },
          ],
        });
      }),
    );
    renderView();

    await userEvent.click(
      await screen.findByRole("checkbox", { name: "Select Unshared Widget" }),
    );
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Select Shared Widget" }),
    );
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "New visibility for selected designs" }),
      "members",
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      /Everyone signed in to this node/,
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Apply members to 2 designs" }),
    );

    expect(await screen.findByText("Changed")).toBeInTheDocument();
    expect(screen.getByText("Not yours")).toBeInTheDocument();
    expect(posted).toEqual({ ids: ["d1", "d2"], visibility: "members" });
  });

  it("offers no apply button until records and a level are chosen", async () => {
    setToken("tok");
    myDesigns([{ id: "d1", title: "Unshared Widget", visibility: "private" }]);
    renderView();

    await screen.findByText("Unshared Widget");
    expect(
      screen.queryByRole("button", { name: /Apply .* designs?/ }),
    ).not.toBeInTheDocument();
  });

  it("says you have made nothing when you have no designs", async () => {
    setToken("tok");
    myDesigns([]);
    renderView();

    expect(
      await screen.findByText(/You have not created a design yet/),
    ).toBeInTheDocument();
  });
});

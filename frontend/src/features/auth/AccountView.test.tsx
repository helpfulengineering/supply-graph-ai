import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
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

function okhList(items: unknown[]) {
  server.use(
    http.get("*/v1/api/okh", () =>
      HttpResponse.json({
        items,
        pagination: {
          page: 1,
          page_size: 100,
          total_items: items.length,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        },
      }),
    ),
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

  it("lists the records only the signed-in visitor can see", async () => {
    setToken("tok");
    okhList([
      { id: "d1", title: "Unshared Widget", visibility: "private" },
      { id: "d2", title: "Shared Widget", visibility: "public" },
    ]);
    renderView();

    expect(await screen.findByText("Unshared Widget")).toBeInTheDocument();
    // A shared record is indistinguishable from anyone else's, so it is not
    // claimed as "yours" here.
    expect(screen.queryByText("Shared Widget")).not.toBeInTheDocument();
  });

  it("distinguishes having made nothing from having shared everything", async () => {
    setToken("tok");
    okhList([{ id: "d2", title: "Shared Widget", visibility: "public" }]);
    renderView();

    expect(
      await screen.findByText(/Every design you can see is shared/),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/You have not created a design yet/),
    ).not.toBeInTheDocument();
  });

  it("says you have made nothing when the catalogue is empty", async () => {
    setToken("tok");
    okhList([]);
    renderView();

    expect(
      await screen.findByText(/You have not created a design yet/),
    ).toBeInTheDocument();
  });
});

import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import { CuratedListPage, CuratedListsPage } from "./CuratedLists";

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ signedIn: true, reportAuthFailure: vi.fn() }),
}));

const LIST = {
  list_id: "field-designs",
  name: "Field designs",
  publisher_did: "did:key:zNode",
  sequence: 1,
  entries: [{ content_hash: "sha256:abc" }],
  signature: "00",
};

function renderPage(node: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  );
}

describe("Curated lists", () => {
  it("shows a published list and publishes a new one", async () => {
    const user = userEvent.setup();
    const calls: unknown[] = [];
    server.use(
      http.get("*/v1/api/federation/lists", () => HttpResponse.json([LIST])),
      http.post("*/v1/api/federation/lists", async ({ request }) => {
        calls.push(await request.json());
        return HttpResponse.json(
          { ...LIST, list_id: "new-list", name: "Shelter" },
          { status: 201 },
        );
      }),
    );

    renderPage(<CuratedListsPage />);
    expect(await screen.findByRole("link", { name: "Field designs" })).toHaveAttribute(
      "href",
      "/lists/field-designs",
    );

    await user.type(screen.getByLabelText("Name"), "Shelter");
    await user.type(
      screen.getByLabelText("Pins"),
      "sha256:def replaces sha256:abc",
    );
    await user.click(screen.getByRole("button", { name: "Publish" }));

    await waitFor(() =>
      expect(calls).toEqual([
        {
          name: "Shelter",
          entries: [{ content_hash: "sha256:def", supersedes: "sha256:abc" }],
        },
      ]),
    );
  });

  it("shows the pins and publishes the next version", async () => {
    const user = userEvent.setup();
    const calls: unknown[] = [];
    server.use(
      http.get("*/v1/api/federation/lists/field-designs", () =>
        HttpResponse.json(LIST),
      ),
      http.put("*/v1/api/federation/lists/field-designs", async ({ request }) => {
        calls.push(await request.json());
        return HttpResponse.json({ ...LIST, sequence: 2 });
      }),
    );

    renderPage(<CuratedListPage listId="field-designs" />);
    expect(await screen.findByRole("listitem")).toHaveTextContent("sha256:abc");
    expect(screen.getByText(/Signed by did:key:zNode/)).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Pins"));
    await user.type(screen.getByLabelText("Pins"), "sha256:def");
    await user.click(screen.getByRole("button", { name: "Publish this version" }));

    await waitFor(() =>
      expect(calls).toEqual([
        { name: "Field designs", entries: [{ content_hash: "sha256:def" }] },
      ]),
    );
  });
});

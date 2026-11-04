import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "../../context/AuthContext";
import { server } from "../../test/msw/server";
import { setToken } from "../auth/tokenStorage";
import { AuthorshipPanel } from "./AuthorshipPanel";

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <AuthorshipPanel kind="okh" id="d1" />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("AuthorshipPanel", () => {
  it("shows an organisation this node could not check as unverified", async () => {
    server.use(
      http.get("*/v1/api/okh/d1/provenance", () =>
        HttpResponse.json({
          authored_by: [],
          published_by: "did:key:zAda",
          on_behalf_of: "did:key:zFab",
          organisation_verified: false,
        }),
      ),
    );
    renderPanel();
    expect(await screen.findByText("did:key:zFab")).toBeInTheDocument();
    expect(
      screen.getByText("Unverified — this node could not check"),
    ).toBeInTheDocument();
  });

  it("shows a chain that holds as verified", async () => {
    server.use(
      http.get("*/v1/api/okh/d1/provenance", () =>
        HttpResponse.json({
          authored_by: [],
          published_by: "did:key:zAda",
          on_behalf_of: "did:key:zFab",
          organisation_verified: true,
        }),
      ),
    );
    renderPanel();
    expect(await screen.findByText("Verified")).toBeInTheDocument();
  });

  it("attributes this design to an organisation the caller holds", async () => {
    setToken("tok");
    let posted: unknown = null;
    server.use(
      http.get("*/v1/api/okh/d1/provenance", () =>
        HttpResponse.json({
          authored_by: [],
          published_by: "did:key:zAda",
          on_behalf_of: null,
        }),
      ),
      http.get("*/v1/api/identity/affiliations", () =>
        HttpResponse.json([
          {
            space_did: "did:key:zFab",
            display_name: "FabLab",
            expires_at: "2026-12-01T00:00:00Z",
          },
        ]),
      ),
      http.put("*/v1/api/okh/d1/attribution", async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json({
          authored_by: [],
          published_by: "did:key:zAda",
          on_behalf_of: "did:key:zFab",
        });
      }),
    );
    renderPanel();

    await userEvent.selectOptions(
      await screen.findByRole("combobox", { name: "Organisation" }),
      "did:key:zFab",
    );
    await userEvent.click(screen.getByRole("button", { name: "Attribute" }));

    expect(posted).toEqual({ on_behalf_of: "did:key:zFab" });
  });
});

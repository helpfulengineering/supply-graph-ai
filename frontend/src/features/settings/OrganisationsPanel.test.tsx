import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import { OrganisationsPanel } from "./OrganisationsPanel";

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ reportAuthFailure: vi.fn() }),
}));

const ORG = {
  space_did: "did:key:zFab",
  display_name: "FabLab",
  members: [
    {
      subject_did: "did:key:zAda",
      display_name: "Ada",
      grant_id: "11111111-1111-4111-8111-111111111111",
      expires_at: "2026-12-01T00:00:00Z",
    },
  ],
};

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <OrganisationsPanel />
    </QueryClientProvider>,
  );
}

describe("OrganisationsPanel", () => {
  it("shows each affiliation's expiry and can affiliate, renew, and unaffiliate", async () => {
    const user = userEvent.setup();
    const calls: string[] = [];
    server.use(
      http.get("*/v1/api/identity/affiliations/administered", () =>
        HttpResponse.json([ORG]),
      ),
      http.post("*/v1/api/identity/affiliations", async ({ request }) => {
        calls.push(`add ${JSON.stringify(await request.json())}`);
        return HttpResponse.json(
          { grant_id: "22222222-2222-4222-8222-222222222222" },
          { status: 201 },
        );
      }),
      http.post("*/v1/api/identity/affiliations/:grantId/renew", ({ params }) => {
        calls.push(`renew ${params.grantId}`);
        return HttpResponse.json(
          { grant_id: "33333333-3333-4333-8333-333333333333" },
          { status: 201 },
        );
      }),
      http.delete("*/v1/api/identity/affiliations/:grantId", ({ params }) => {
        calls.push(`revoke ${params.grantId}`);
        return HttpResponse.json({ success: true });
      }),
    );

    renderPanel();
    expect(await screen.findByRole("heading", { name: "FabLab" })).toBeInTheDocument();
    expect(screen.getByText("Ada")).toBeInTheDocument();
    expect(screen.getByText(/Expires 2026-12-01/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Person"), "did:key:zBob");
    await user.click(screen.getByRole("button", { name: "Affiliate" }));
    await user.click(screen.getByRole("button", { name: "Renew" }));
    await user.click(screen.getByRole("button", { name: "Unaffiliate" }));

    await waitFor(() =>
      expect(calls).toEqual([
        'add {"space_did":"did:key:zFab","subject_did":"did:key:zBob"}',
        "renew 11111111-1111-4111-8111-111111111111",
        "revoke 11111111-1111-4111-8111-111111111111",
      ]),
    );
  });
});

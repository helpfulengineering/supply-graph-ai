import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { AuthProvider } from "../../context/AuthContext";
import { InvitesPanel } from "./InvitesPanel";

const invite = {
  invite_id: "11111111-1111-4111-8111-111111111111",
  expires_at: "2026-12-01T00:00:00Z",
  use_limit: null,
  uses: 0,
  revoked: false,
};

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <InvitesPanel />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("InvitesPanel", () => {
  it("lists an invite and revokes it", async () => {
    let rows = [invite];
    server.use(
      http.get("*/v1/api/identity/invites", () => HttpResponse.json(rows)),
      http.post("*/v1/api/identity/invites/:id/revoke", () => {
        rows = [{ ...invite, revoked: true }];
        return HttpResponse.json(rows[0]);
      }),
    );
    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findByText(invite.invite_id)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Revoke" }));
    expect(await screen.findByText("Revoked")).toBeInTheDocument();
  });

  it("mints an invite and shows the link once", async () => {
    let sent: unknown;
    server.use(
      http.get("*/v1/api/identity/invites", () => HttpResponse.json([])),
      http.post("*/v1/api/identity/invites", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(
          {
            invite_id: "22222222-2222-4222-8222-222222222222",
            token: "minted-token",
            expires_at: "2026-12-01T00:00:00Z",
            use_limit: null,
          },
          { status: 201 },
        );
      }),
    );
    const user = userEvent.setup();
    renderPanel();

    await user.click(
      await screen.findByRole("button", { name: "Mint invite" }),
    );
    expect(sent).toMatchObject({ ttl_days: 7 });
    expect(
      await screen.findByText(/register\?invite=minted-token/),
    ).toBeInTheDocument();
  });
});

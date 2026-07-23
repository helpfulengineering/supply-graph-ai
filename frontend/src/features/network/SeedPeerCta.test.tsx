import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import { SeedPeerCta } from "./SeedPeerCta";

const authState = { hasWrite: true };

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    hasWrite: authState.hasWrite,
    reportAuthFailure: vi.fn(),
  }),
}));

function renderCta() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <SeedPeerCta />
    </QueryClientProvider>,
  );
}

describe("SeedPeerCta", () => {
  beforeEach(() => {
    authState.hasWrite = true;
  });

  it("renders when status includes seed_peer_url and runs seed sync", async () => {
    const user = userEvent.setup();
    let okwSync = 0;
    server.use(
      http.post("*/v1/api/federation/okw/sync/run", () => {
        okwSync += 1;
        return HttpResponse.json({
          results: [],
          total_pulled: 2,
        });
      }),
    );
    renderCta();
    expect(
      await screen.findByRole("button", { name: /Follow & sync seed peer/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/openhardwaremanager\.org/i)).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: /Follow & sync seed peer/i }),
    );
    await waitFor(() => {
      expect(okwSync).toBe(1);
      expect(screen.getByText(/Synced 2 OKW/i)).toBeInTheDocument();
    });
  });

  it("hides when seed_peer_url is empty", async () => {
    server.use(
      http.get("*/v1/api/federation/status", () =>
        HttpResponse.json({
          did: "did:key:zLocal",
          display_name: "Local",
          role: "peer",
          catalog_record_count: 0,
          merkle_root: "",
          peer_count: 0,
          followed_peer_count: 0,
          sync_interval_sec: 60,
          mdns_enabled: false,
          background_sync_running: false,
          manual_peers: [],
          seed_peer_url: null,
          metrics: {},
        }),
      ),
    );
    const { container } = renderCta();
    await waitFor(() => {
      expect(container).toBeEmptyDOMElement();
    });
  });

  it("hides when federation is disabled (404)", async () => {
    server.use(
      http.get("*/v1/api/federation/status", () =>
        HttpResponse.json({ detail: "Federation is not enabled" }, { status: 404 }),
      ),
    );
    const { container } = renderCta();
    await waitFor(() => {
      expect(container).toBeEmptyDOMElement();
    });
  });
});

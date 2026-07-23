import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import { NetworkView } from "./NetworkView";

const authState = { hasWrite: true };

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ hasWrite: authState.hasWrite }),
}));

function renderNetwork() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <NetworkView />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NetworkView empty state", () => {
  beforeEach(() => {
    authState.hasWrite = true;
    server.use(
      http.get("*/v1/api/okw/spaces", () =>
        HttpResponse.json({
          success: true,
          spaces: [],
          total: 0,
          local_count: 0,
          mom_count: 0,
          dropped_no_coords: 0,
          mom_available: true,
        }),
      ),
    );
  });

  it("offers New facility when the user can write", async () => {
    renderNetwork();
    expect(await screen.findByText(/No spaces yet/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^New facility$/i }).length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Create your first local facility/i),
    ).toBeInTheDocument();
  });

  it("offers Connect API key when the user cannot write", async () => {
    authState.hasWrite = false;
    renderNetwork();
    expect(await screen.findByText(/No spaces yet/i)).toBeInTheDocument();
    // Header + empty-state both expose the smart CTA.
    expect(screen.getAllByRole("button", { name: /Connect API key/i }).length).toBeGreaterThan(0);
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SharingPanel } from "./SharingPanel";

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    hasWrite: true,
    reportAuthFailure: vi.fn(),
  }),
}));

describe("SharingPanel", () => {
  it("composes visibility and disclosure under one Sharing heading", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <SharingPanel id="okw-1" />
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("heading", { name: /^Sharing$/i })).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: /Who can receive this/i }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: /How much they see/i }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/Nothing is exported while visibility is private/i),
    ).toBeInTheDocument();
  });
});

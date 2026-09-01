import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "../../context/AuthContext";
import { LLMCredentialsPanel } from "./LLMCredentialsPanel";

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <LLMCredentialsPanel />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("LLMCredentialsPanel", () => {
  it("marks a credential the node cannot decrypt, and says what to do", async () => {
    renderPanel();

    // The fixture's openai row is stored but unreadable — the production
    // shape: present in the listing, unusable by the runtime.
    expect(await screen.findByText("unreadable")).toBeInTheDocument();
    expect(screen.getByText(/cannot be decrypted/i)).toBeInTheDocument();
    expect(screen.getByText(/Save the key again/i)).toBeInTheDocument();
  });

  it("offers no way to activate a key that cannot be read", async () => {
    renderPanel();
    await screen.findByText("unreadable");

    // anthropic is already active, openai is unreadable — so neither row
    // should offer activation, and the button should be absent entirely.
    expect(screen.queryByRole("button", { name: /make active/i })).toBeNull();
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import {
  identityFixture,
  spaceIdentityFixture,
  whoamiAdminFixture,
} from "../../test/fixtures";
import { AuthProvider } from "../../context/AuthContext";
import { SpacesPanel } from "./SpacesPanel";

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <SpacesPanel />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("SpacesPanel", () => {
  it("explains TOFU and links the fields to where their values come from", async () => {
    renderPanel();

    expect(
      await screen.findByText(/trust on first use/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/creating a new one\? generate a fresh did/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/settings → identities, or mint one below/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "/v1/docs" })).toHaveAttribute(
      "href",
      "/v1/docs",
    );
  });

  it("autofills the admin DID from the session's own identity", async () => {
    server.use(
      http.get("*/v1/api/identity/whoami", () =>
        HttpResponse.json({
          ...whoamiAdminFixture,
          subject_did: identityFixture.did,
        }),
      ),
    );
    renderPanel();

    await waitFor(() =>
      expect(screen.getByLabelText(/admin did/i)).toHaveValue(
        identityFixture.did,
      ),
    );
    // A session that already has a person DID doesn't need the mint shortcut.
    expect(
      screen.queryByRole("button", { name: /mint a person identity/i }),
    ).not.toBeInTheDocument();
  });

  it("offers to mint a person identity when the session has none bound", async () => {
    // Default fixture: whoamiAdminFixture.subject_did is null — the
    // bootstrap admin key, which is what a fresh install's first operator
    // actually has (friction log entry 08).
    const user = userEvent.setup();
    renderPanel();

    const mintButton = await screen.findByRole("button", {
      name: /mint a person identity for me/i,
    });
    await user.click(mintButton);

    await waitFor(() =>
      expect(screen.getByLabelText(/admin did/i)).toHaveValue(
        identityFixture.did,
      ),
    );
  });

  it("generates a fresh space DID instead of requiring one up front", async () => {
    const user = userEvent.setup();
    renderPanel();

    const generateButton = await screen.findByRole("button", {
      name: /generate a new space did/i,
    });
    await user.click(generateButton);

    // The mock always returns identityFixture regardless of the requested
    // kind, so this asserts the panel wires the mint result into the field —
    // not that the server picked "space".
    await waitFor(() =>
      expect(screen.getByLabelText(/space did/i)).toHaveValue(
        identityFixture.did,
      ),
    );
  });

  it("rejects an obvious typo before it can reach the server", async () => {
    const user = userEvent.setup();
    renderPanel();

    const spaceInput = await screen.findByLabelText(/space did/i);
    await user.type(spaceInput, "not-a-did");
    await user.tab();

    expect(
      await screen.findByText(/doesn't look like a did/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Claim" })).toBeDisabled();
  });

  it("requires an explicit confirmation before Claim is enabled", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.type(
      await screen.findByLabelText(/space did/i),
      spaceIdentityFixture.did,
    );
    await user.type(
      screen.getByLabelText(/admin did/i),
      identityFixture.did,
    );

    // Both fields are valid, but nothing was checked yet.
    const claimButton = screen.getByRole("button", { name: "Claim" });
    expect(claimButton).toBeDisabled();

    const confirmCheckbox = await screen.findByRole("checkbox");
    expect(confirmCheckbox).toHaveAccessibleName(
      new RegExp(
        `binds.*${identityFixture.did}.*admin of.*${spaceIdentityFixture.did}`,
      ),
    );
    await user.click(confirmCheckbox);
    expect(claimButton).toBeEnabled();

    await user.click(claimButton);
    expect(
      await screen.findByText(`Claimed ${spaceIdentityFixture.did}`),
    ).toBeInTheDocument();
  });

  it("un-confirms if a field changes after the box was checked", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.type(
      await screen.findByLabelText(/space did/i),
      spaceIdentityFixture.did,
    );
    await user.type(
      screen.getByLabelText(/admin did/i),
      identityFixture.did,
    );
    await user.click(await screen.findByRole("checkbox"));
    expect(screen.getByRole("button", { name: "Claim" })).toBeEnabled();

    await user.type(screen.getByLabelText(/space did/i), "x");
    expect(screen.getByRole("button", { name: "Claim" })).toBeDisabled();
  });
});

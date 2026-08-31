import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { storageConfigFixture } from "../../test/fixtures";
import { AuthProvider } from "../../context/AuthContext";
import { StoragePanel } from "./StoragePanel";

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <StoragePanel />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("StoragePanel", () => {
  it("shows the current configuration and what actually answered", async () => {
    renderPanel();

    // Anchored on the fingerprint, which only the loaded config section
    // renders. "Local filesystem" would resolve instantly from the form's
    // provider <option> and the assertion would never wait for the query.
    expect(
      await screen.findByText(/12 designs, 5 facilities/),
    ).toBeInTheDocument();

    // The bucket appears twice on purpose: once as what is configured, once
    // as what the fingerprint actually reached. They can disagree, which is
    // the first thing worth knowing when storage misbehaves.
    expect(screen.getAllByText(/\/var\/ohm-data/).length).toBe(2);
    expect(screen.getByText("Read from")).toBeInTheDocument();
  });

  it("never renders a credential value, only which names are set", async () => {
    server.use(
      http.get("*/v1/api/storage/config", () =>
        HttpResponse.json({
          ...storageConfigFixture,
          data: {
            ...storageConfigFixture.data,
            config: {
              ...storageConfigFixture.data.config,
              provider: "azure_blob",
              credential_names: ["account_key", "account_name"],
            },
          },
        }),
      ),
    );
    const { container } = renderPanel();

    expect(await screen.findByText("account_key")).toBeInTheDocument();
    // The API cannot return a value, so there is nothing to leak — this holds
    // the UI to reading only what it is given.
    expect(container.textContent).not.toMatch(/secret|password=/i);
  });

  it("reports which prefixes were created after a successful switch", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.type(await screen.findByLabelText(/^path$/i), "~/ohm-data");
    await user.click(
      screen.getByRole("button", { name: /validate and switch/i }),
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      /Created okh\/, okw\/, packages\/, supply-trees\//,
    );
    // Where the data it left behind went is part of the outcome.
    expect(screen.getByRole("status")).toHaveTextContent(/untouched/);
  });

  it("says the instance is still serving when validation fails", async () => {
    // The server's own wording. It is the only layer that knows the switch did
    // not take effect, so the panel surfaces its message rather than guessing.
    server.use(
      http.post("*/v1/api/storage/config", () =>
        HttpResponse.json(
          {
            detail:
              "Connected, but could not write to the backend: read-only bucket. " +
              "The instance is still serving from its previous configuration.",
          },
          { status: 400 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderPanel();

    await user.type(await screen.findByLabelText(/^path$/i), "/nope");
    await user.click(
      screen.getByRole("button", { name: /validate and switch/i }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not write to the backend/i);
    expect(alert).toHaveTextContent(/still serving from its previous/i);
  });

  it("offers the credential fields the chosen provider actually takes", async () => {
    const user = userEvent.setup();
    renderPanel();

    // Local storage needs none, so none are offered.
    await screen.findByLabelText(/^path$/i);
    expect(screen.queryByLabelText("account_key")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/provider/i), "azure_blob");

    expect(await screen.findByLabelText("account_key")).toBeInTheDocument();
    expect(screen.getByLabelText("account_name")).toBeInTheDocument();
    // An S3 field must not be offered for Azure: the server rejects an
    // unrecognised credential name rather than dropping it.
    expect(screen.queryByLabelText("access_key_id")).not.toBeInTheDocument();
  });
});

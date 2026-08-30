import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, beforeEach } from "vitest";
import { server } from "../../test/msw/server";
import { securityPolicyFixture } from "../../test/fixtures";
import { AuthProvider } from "../../context/AuthContext";
import { ToastProvider } from "../../components/ui/Toast";
import { RegisterView } from "./RegisterView";
import { getToken } from "./tokenStorage";

function renderView() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <AuthProvider>
          <RegisterView />
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

describe("RegisterView", () => {
  it("signs the visitor in without a second paste step", async () => {
    const user = userEvent.setup();
    renderView();

    await user.type(
      await screen.findByLabelText(/display name/i),
      "Ada Lovelace",
    );
    await user.click(screen.getByRole("button", { name: "Register" }));

    // The token is shown once for keeping...
    expect(await screen.findByText("ohm_registered_once")).toBeInTheDocument();
    // ...and is already the session, so nothing has to be pasted back.
    expect(getToken()).toBe("ohm_registered_once");
    expect(await screen.findByText("You are signed in")).toBeInTheDocument();
  });

  it("persists the session it minted, and only in one store", async () => {
    // This reverses what #404 asserted, deliberately. Tab-scoped storage was
    // the right call when the only user was an operator pasting an admin key;
    // a member of the public who registered is a different user, and making
    // them re-enter a 43-character secret per tab is the pressure that teaches
    // people to keep credentials somewhere careless. It is only an acceptable
    // trade because these keys now expire (#413) and their owner can revoke
    // them (#413) — a pasted key is still tab-scoped, see tokenStorage tests.
    const user = userEvent.setup();
    renderView();

    await user.type(await screen.findByLabelText(/display name/i), "Ada");
    await user.click(screen.getByRole("button", { name: "Register" }));
    await screen.findByText("ohm_registered_once");

    expect(localStorage.getItem("ohm_api_key")).toBe("ohm_registered_once");
    // Never both: signing out of one store would otherwise leave the other
    // holding a live credential.
    expect(sessionStorage.getItem("ohm_api_key")).toBeNull();
  });

  it("shows no form at all when the node has registration closed", async () => {
    server.use(
      http.get("*/v1/api/identity/security-policy", () =>
        HttpResponse.json({
          ...securityPolicyFixture,
          mode: "shielded",
          open_registration: false,
        }),
      ),
    );
    renderView();

    expect(
      await screen.findByText("This node does not accept registrations"),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/display name/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Register" }),
    ).not.toBeInTheDocument();
  });

  it("reports a refusal rather than appearing to succeed", async () => {
    server.use(
      http.post("*/v1/api/identity/register", () =>
        HttpResponse.json({ detail: "Registration is disabled" }, { status: 403 }),
      ),
    );
    const user = userEvent.setup();
    renderView();

    await user.type(await screen.findByLabelText(/display name/i), "Ada");
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(getToken()).toBeNull();
    expect(screen.queryByText("You are signed in")).not.toBeInTheDocument();
  });
});

describe("RegisterView — session persistence (#415)", () => {
  it("keeps a registered visitor signed in across tabs", async () => {
    const user = userEvent.setup();
    renderView();

    await user.type(await screen.findByLabelText(/display name/i), "Ada");
    await user.click(screen.getByRole("button", { name: "Register" }));
    await screen.findByText("ohm_registered_once");

    // Reopening the tab clears sessionStorage; a minted session survives it.
    sessionStorage.clear();
    expect(getToken()).toBe("ohm_registered_once");
  });

  it("still keeps the credential out of a pasted session's store", async () => {
    const user = userEvent.setup();
    renderView();

    await user.type(await screen.findByLabelText(/display name/i), "Ada");
    await user.click(screen.getByRole("button", { name: "Register" }));
    await screen.findByText("ohm_registered_once");

    // It persists deliberately — but only because these keys now expire and
    // their owner can revoke them. It must never be in BOTH stores, or signing
    // out of one would leave the other holding a live credential.
    expect(sessionStorage.getItem("ohm_api_key")).toBeNull();
  });
});

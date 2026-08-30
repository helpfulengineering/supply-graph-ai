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

  it("never writes the token to localStorage", async () => {
    const user = userEvent.setup();
    renderView();

    await user.type(await screen.findByLabelText(/display name/i), "Ada");
    await user.click(screen.getByRole("button", { name: "Register" }));
    await screen.findByText("ohm_registered_once");

    // The app does use localStorage elsewhere (theme, domain preference), so
    // the check is that the credential never reaches it — not that it is empty.
    expect(JSON.stringify({ ...localStorage })).not.toContain(
      "ohm_registered_once",
    );
    expect(sessionStorage.getItem("ohm_api_key")).toBe("ohm_registered_once");
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

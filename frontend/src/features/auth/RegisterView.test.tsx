import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, beforeEach } from "vitest";
import { server } from "../../test/msw/server";
import {
  registrationFixture,
  securityPolicyFixture,
} from "../../test/fixtures";
import { setMockNavigation } from "../../test/nextNavigation";
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

async function registerAs(
  user: ReturnType<typeof userEvent.setup>,
  name: string,
) {
  await user.type(await screen.findByLabelText("Username"), "ada");
  await user.type(screen.getByLabelText("Password"), "correct horse");
  await user.type(screen.getByLabelText(/display name/i), name);
  await user.click(screen.getByRole("button", { name: "Register" }));
}

describe("RegisterView", () => {
  it("signs the visitor in without handing them a token", async () => {
    const user = userEvent.setup();
    renderView();

    await registerAs(user, "Ada Lovelace");

    expect(await screen.findByText("ohm_recovery_once")).toBeInTheDocument();
    expect(screen.queryByText("ohm_registered_once")).not.toBeInTheDocument();
    expect(getToken()).toBeNull();
    expect(await screen.findByText("You are signed in")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Download" }),
    ).toBeInTheDocument();
    const proceed = screen.getByRole("button", { name: "Continue" });
    expect(proceed).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /saved/i }));
    expect(proceed).toBeEnabled();
  });

  it("does not store an API token in either web store", async () => {
    const user = userEvent.setup();
    renderView();

    await registerAs(user, "Ada");
    await screen.findByText("ohm_recovery_once");

    expect(localStorage.getItem("ohm_api_key")).toBeNull();
    expect(sessionStorage.getItem("ohm_api_key")).toBeNull();
    expect(localStorage.getItem("ohm_session_hint")).toBe("1");
  });

  it("registers from an invite link and names the node", async () => {
    setMockNavigation({ pathname: "/register", search: "invite=invite-token" });
    let sent: unknown;
    server.use(
      http.get("*/v1/api/identity/security-policy", () =>
        HttpResponse.json({
          ...securityPolicyFixture,
          open_registration: true,
          registration: "invite",
        }),
      ),
      http.post("*/v1/api/identity/register", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(registrationFixture, { status: 201 });
      }),
    );
    const user = userEvent.setup();
    renderView();

    expect(
      await screen.findByText(securityPolicyFixture.node_name),
    ).toBeInTheDocument();
    expect(
      screen.getByText(securityPolicyFixture.operator_name),
    ).toBeInTheDocument();
    await registerAs(user, "Ada Lovelace");
    expect(sent).toMatchObject({ invite: "invite-token" });
  });

  it("tells an invite-only node that a link is required", async () => {
    server.use(
      http.get("*/v1/api/identity/security-policy", () =>
        HttpResponse.json({
          ...securityPolicyFixture,
          open_registration: true,
          registration: "invite",
        }),
      ),
    );
    renderView();

    expect(
      await screen.findByText(
        "This node only accepts a registration that carries an invite.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/display name/i)).not.toBeInTheDocument();
  });

  it("shows no form at all when the node has registration closed", async () => {
    server.use(
      http.get("*/v1/api/identity/security-policy", () =>
        HttpResponse.json({
          ...securityPolicyFixture,
          mode: "shielded",
          open_registration: false,
          registration: "closed",
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
        HttpResponse.json(
          { detail: "Registration is disabled" },
          { status: 403 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderView();

    await registerAs(user, "Ada");

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(getToken()).toBeNull();
    expect(screen.queryByText("You are signed in")).not.toBeInTheDocument();
  });
});

describe("RegisterView — session (#570)", () => {
  it("offers a way to sign in", async () => {
    renderView();
    expect(
      await screen.findByRole("link", { name: "Sign in" }),
    ).toHaveAttribute("href", "/login");
  });
});

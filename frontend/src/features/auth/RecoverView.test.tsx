import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, beforeEach } from "vitest";
import { server } from "../../test/msw/server";
import { securityPolicyFixture } from "../../test/fixtures";
import { AuthProvider } from "../../context/AuthContext";
import { ToastProvider } from "../../components/ui/Toast";
import { RecoverView } from "./RecoverView";
import { getToken } from "./tokenStorage";

function renderView() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <AuthProvider>
          <RecoverView />
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

describe("RecoverView", () => {
  it("signs the visitor back in and issues a replacement code", async () => {
    const user = userEvent.setup();
    renderView();

    await user.type(await screen.findByLabelText(/recovery code/i), "ohm_recovery_once");
    await user.click(screen.getByRole("button", { name: "Recover account" }));

    expect(await screen.findByText("ohm_recovered_token")).toBeInTheDocument();
    // The code just used is spent, so a replacement has to be shown.
    expect(screen.getByText("ohm_recovery_replacement")).toBeInTheDocument();
    expect(getToken()).toBe("ohm_recovered_token");
  });

  it("labels the two secrets distinctly", async () => {
    const user = userEvent.setup();
    renderView();

    await user.type(await screen.findByLabelText(/recovery code/i), "x");
    await user.click(screen.getByRole("button", { name: "Recover account" }));

    await screen.findByText("ohm_recovered_token");
    // Two one-time panels on screen at once; each must say which secret it is,
    // or the reader stores the wrong one.
    expect(screen.getByText("Save your new recovery code")).toBeInTheDocument();
    expect(screen.getByText("Copy this token now")).toBeInTheDocument();
  });

  it("reports a bad code rather than appearing to succeed", async () => {
    server.use(
      http.post("*/v1/api/identity/recover", () =>
        HttpResponse.json({ detail: "That recovery code is not valid" }, { status: 401 }),
      ),
    );
    const user = userEvent.setup();
    renderView();

    await user.type(await screen.findByLabelText(/recovery code/i), "wrong");
    await user.click(screen.getByRole("button", { name: "Recover account" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("shows no form at all when the node has recovery closed", async () => {
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
      await screen.findByText("This node does not accept self-service recovery"),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/recovery code/i)).not.toBeInTheDocument();
  });
});

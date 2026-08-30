import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, beforeEach, vi } from "vitest";
import { server } from "../../test/msw/server";
import { AuthProvider } from "../../context/AuthContext";
import { ToastProvider } from "../../components/ui/Toast";
import { MyKeysPanel } from "./MyKeysPanel";
import { setToken } from "./tokenStorage";

const CURRENT_KEY = "00000000-0000-0000-0000-0000000000aa";

function key(id: string, name: string, extra: Record<string, unknown> = {}) {
  return {
    key_id: id,
    name,
    permissions: ["read", "write"],
    created_at: "2026-08-01T00:00:00Z",
    revoked: false,
    ...extra,
  };
}

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <AuthProvider>
          <MyKeysPanel />
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  sessionStorage.clear();
  setToken("tok");
});

describe("MyKeysPanel", () => {
  it("marks the key in use and refuses to revoke it", async () => {
    server.use(
      http.get("*/v1/api/identity/keys", () =>
        HttpResponse.json([key(CURRENT_KEY, "this-browser"), key("other", "laptop-cli")]),
      ),
    );
    renderPanel();

    expect(await screen.findByText("this-browser")).toBeInTheDocument();
    expect(screen.getByText("this session")).toBeInTheDocument();

    // Revoking the key you are holding signs you out mid-click, with no way
    // back except the recovery code.
    const buttons = screen.getAllByRole("button", { name: "Revoke" });
    expect(buttons[0]).toBeDisabled();
    expect(buttons[1]).toBeEnabled();
  });

  it("flags an expiry close enough to act on, and stays quiet otherwise", async () => {
    const soon = new Date(Date.now() + 5 * 86_400_000).toISOString();
    const distant = new Date(Date.now() + 200 * 86_400_000).toISOString();
    server.use(
      http.get("*/v1/api/identity/keys", () =>
        HttpResponse.json([
          key("a", "expiring", { expires_at: soon }),
          key("b", "fine", { expires_at: distant }),
        ]),
      ),
    );
    renderPanel();

    expect(await screen.findByText(/expires in 5 days/)).toBeInTheDocument();
    expect(screen.queryByText(/expires in 200/)).not.toBeInTheDocument();
  });

  it("creates a named key and shows its token once", async () => {
    server.use(
      http.get("*/v1/api/identity/keys", () => HttpResponse.json([])),
      http.post("*/v1/api/identity/keys", () =>
        HttpResponse.json(key("new", "laptop-cli", { token: "ohm_new_key" }), {
          status: 201,
        }),
      ),
    );
    const user = userEvent.setup();
    renderPanel();

    await user.type(await screen.findByLabelText(/new key name/i), "laptop-cli");
    await user.click(screen.getByRole("button", { name: "Create key" }));

    expect(await screen.findByText("ohm_new_key")).toBeInTheDocument();
  });

  it("offers the panic button for a key that went somewhere it should not have", async () => {
    const revokeOthers = vi.fn(() =>
      HttpResponse.json({ success: true, message: "Revoked 2 other key(s) on your account" }),
    );
    server.use(
      http.get("*/v1/api/identity/keys", () => HttpResponse.json([key("a", "one")])),
      http.post("*/v1/api/identity/keys/revoke-others", revokeOthers),
    );
    const user = userEvent.setup();
    renderPanel();

    await user.click(
      await screen.findByRole("button", { name: /Revoke every key but this one/ }),
    );

    expect(revokeOthers).toHaveBeenCalled();
  });
});

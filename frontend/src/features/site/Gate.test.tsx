import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Gate } from "./Gate";
import type { GateCopy } from "../../lib/site/stack";

const signIn = vi.fn<(name: string, email: string) => Promise<boolean>>();

vi.mock("../../lib/site/stack", () => ({
  signIn: (name: string, email: string) => signIn(name, email),
}));

const COPY: GateCopy = {
  enabled: true,
  title: "Sign in to Mission Control",
  body: "This site keeps a record of who visited.",
  fine: "Grants nothing in OHM.",
};

function renderGate(overrides: Partial<GateCopy> = {}) {
  const onSignedIn = vi.fn();
  const onDismiss = vi.fn();
  render(
    <Gate copy={{ ...COPY, ...overrides }} onSignedIn={onSignedIn} onDismiss={onDismiss} />,
  );
  return { onSignedIn, onDismiss };
}

describe("Gate", () => {
  beforeEach(() => {
    signIn.mockReset();
    signIn.mockResolvedValue(true);
  });

  it("presents the operator's copy as a modal dialog", () => {
    renderGate({ title: "Members only", fine: "House rules apply." });

    const dialog = screen.getByRole("dialog", { name: "Members only" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("This site keeps a record of who visited.")).toBeInTheDocument();
    expect(screen.getByText("House rules apply.")).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveFocus();
  });

  it("reports bad input under the field instead of calling the RPC", async () => {
    const user = userEvent.setup();
    const { onSignedIn } = renderGate();

    await user.type(screen.getByLabelText("Name"), "Ada");
    await user.type(screen.getByLabelText("Email"), "ada@example");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText(/valid email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(signIn).not.toHaveBeenCalled();
    expect(onSignedIn).not.toHaveBeenCalled();
  });

  it("signs in with the values the RPC will store, then hands back", async () => {
    const user = userEvent.setup();
    const { onSignedIn } = renderGate();

    await user.type(screen.getByLabelText("Name"), "  Ada Lovelace  ");
    await user.type(screen.getByLabelText("Email"), "  Ada@Example.org  ");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(signIn).toHaveBeenCalledWith("Ada Lovelace", "ada@example.org");
    expect(onSignedIn).toHaveBeenCalledTimes(1);
  });

  it("says so when sign-in fails, and says the app is unaffected", async () => {
    signIn.mockResolvedValue(false);
    const user = userEvent.setup();
    const { onSignedIn } = renderGate();

    await user.type(screen.getByLabelText("Name"), "Ada");
    await user.type(screen.getByLabelText("Email"), "ada@example.org");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/rest of OHM is unaffected/i);
    expect(onSignedIn).not.toHaveBeenCalled();
  });

  it("is dismissible — the gate stands in front of one page, not the app", async () => {
    const user = userEvent.setup();
    const { onDismiss } = renderGate();

    await user.click(screen.getByRole("button", { name: "Not now" }));
    expect(onDismiss).toHaveBeenCalledTimes(1);

    await user.keyboard("{Escape}");
    expect(onDismiss).toHaveBeenCalledTimes(2);
  });
});

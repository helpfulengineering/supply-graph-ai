import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VisitorDirectory } from "./VisitorDirectory";

const calls = {
  adminUpdateVisitor: vi.fn(),
  adminDeleteVisitor: vi.fn(),
  adminVisitors: vi.fn(),
  visitorsMasked: vi.fn(),
};
const responses = {
  admin: { ok: true, data: [entry()] },
  masked: { ok: true, data: [entry({ email: "a***@e***", masked: true, firstSeen: null })] },
  update: { ok: true, data: null },
  remove: { ok: true, data: null },
};

function entry(overrides: Record<string, unknown> = {}) {
  return {
    name: "Ada Lovelace",
    email: "ada@example.org",
    masked: false,
    firstSeen: "2026-08-01T09:00:00.000Z",
    lastSeen: "2026-08-11T09:00:00.000Z",
    isAdmin: false,
    ...overrides,
  };
}

vi.mock("../../lib/site/stack", () => ({
  operatorToken: () => "held-token",
  adminVisitors: (t: string) => {
    calls.adminVisitors(t);
    return Promise.resolve(responses.admin);
  },
  visitorsMasked: (e: string) => {
    calls.visitorsMasked(e);
    return Promise.resolve(responses.masked);
  },
  adminUpdateVisitor: (t: string, email: string, changes: unknown) => {
    calls.adminUpdateVisitor(t, email, changes);
    return Promise.resolve(responses.update);
  },
  adminDeleteVisitor: (t: string, email: string) => {
    calls.adminDeleteVisitor(t, email);
    return Promise.resolve(responses.remove);
  },
}));

describe("VisitorDirectory", () => {
  beforeEach(() => {
    Object.values(calls).forEach((c) => c.mockClear());
    responses.admin = { ok: true, data: [entry()] };
    responses.update = { ok: true, data: null };
    responses.remove = { ok: true, data: null };
  });

  it("reads the masked RPC for a signed-in visitor and offers no controls", async () => {
    render(
      <VisitorDirectory email="ada@example.org" isOperator={false} onVisitorChanged={vi.fn()} />,
    );

    await waitFor(() => expect(calls.visitorsMasked).toHaveBeenCalledWith("ada@example.org"));
    expect(calls.adminVisitors).not.toHaveBeenCalled();
    expect(await screen.findByText("a***@e***")).toBeInTheDocument();
    // The controls are keyed to the row's own `masked` flag, so a masked read
    // cannot render an operator affordance even by mistake.
    expect(screen.queryByRole("button", { name: "Rename" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("reads nothing at all for a visitor who has not signed in", async () => {
    render(<VisitorDirectory email={null} isOperator={false} onVisitorChanged={vi.fn()} />);

    await screen.findByText("No visitors recorded yet.");
    expect(calls.visitorsMasked).not.toHaveBeenCalled();
    expect(calls.adminVisitors).not.toHaveBeenCalled();
  });

  it("renames a row through the operator token", async () => {
    const user = userEvent.setup();
    const onVisitorChanged = vi.fn();
    render(
      <VisitorDirectory email={null} isOperator onVisitorChanged={onVisitorChanged} />,
    );

    await user.click(await screen.findByRole("button", { name: "Rename" }));
    const field = screen.getByLabelText("Name for ada@example.org");
    await user.clear(field);
    await user.type(field, "Ada King");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(calls.adminUpdateVisitor).toHaveBeenCalledWith("held-token", "ada@example.org", {
        name: "Ada King",
      }),
    );
    expect(onVisitorChanged).toHaveBeenCalled();
  });

  it("toggles the admin marker without touching the name", async () => {
    const user = userEvent.setup();
    render(<VisitorDirectory email={null} isOperator onVisitorChanged={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Set admin marker" }));

    // Name omitted, not blanked: the RPC coalesces a null name onto the
    // current one, so a marker toggle must not carry a name at all.
    await waitFor(() =>
      expect(calls.adminUpdateVisitor).toHaveBeenCalledWith("held-token", "ada@example.org", {
        isAdmin: true,
      }),
    );
  });

  it("clears an existing admin marker", async () => {
    responses.admin = { ok: true, data: [entry({ isAdmin: true })] };
    const user = userEvent.setup();
    render(<VisitorDirectory email={null} isOperator onVisitorChanged={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Clear admin marker" }));

    await waitFor(() =>
      expect(calls.adminUpdateVisitor).toHaveBeenCalledWith("held-token", "ada@example.org", {
        isAdmin: false,
      }),
    );
  });

  it("deletes only after a confirmation", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<VisitorDirectory email={null} isOperator onVisitorChanged={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Delete" }));
    expect(calls.adminDeleteVisitor).not.toHaveBeenCalled();

    confirm.mockReturnValue(true);
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() =>
      expect(calls.adminDeleteVisitor).toHaveBeenCalledWith("held-token", "ada@example.org"),
    );
    confirm.mockRestore();
  });

  it("renders a refused mutation instead of appearing to succeed", async () => {
    const user = userEvent.setup();
    responses.update = { ok: false, error: "no such visitor" } as never;
    render(<VisitorDirectory email={null} isOperator onVisitorChanged={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Set admin marker" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("no such visitor");
  });

  it("renders a failed read instead of an empty directory", async () => {
    responses.admin = { ok: false, error: "That operator token was not accepted." } as never;
    render(<VisitorDirectory email={null} isOperator onVisitorChanged={vi.fn()} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("not accepted");
  });
});

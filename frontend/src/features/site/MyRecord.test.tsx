import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MyRecord } from "./MyRecord";

/**
 * The self-service tier: the one row a visitor may read unmasked and change,
 * reached by a claim nobody verified. What matters here is that the two rights
 * the panel advertises — rename, erase — are real, and that a refusal is
 * rendered rather than swallowed.
 */
const calls = {
  updateOwnName: vi.fn(),
  deleteOwn: vi.fn(),
};
const responses = {
  record: { ok: true, data: record() },
  update: { ok: true, data: null },
  erase: { ok: true, data: null },
};

function record(overrides: Record<string, unknown> = {}) {
  return {
    name: "Ada Lovelace",
    email: "ada@example.org",
    firstSeen: "2026-08-01T09:00:00.000Z",
    lastSeen: "2026-08-11T09:00:00.000Z",
    isAdmin: false,
    ...overrides,
  };
}

vi.mock("../../lib/site/stack", () => ({
  myRecord: () => Promise.resolve(responses.record),
  updateOwnName: (email: string, name: string) => {
    calls.updateOwnName(email, name);
    return Promise.resolve(responses.update);
  },
  deleteOwn: (email: string) => {
    calls.deleteOwn(email);
    return Promise.resolve(responses.erase);
  },
}));

const visitor = { name: "Ada Lovelace", email: "ada@example.org" };

describe("MyRecord", () => {
  beforeEach(() => {
    calls.updateOwnName.mockClear();
    calls.deleteOwn.mockClear();
    responses.record = { ok: true, data: record() };
    responses.update = { ok: true, data: null };
    responses.erase = { ok: true, data: null };
  });

  it("renames the row and confirms it saved", async () => {
    const user = userEvent.setup();
    render(<MyRecord visitor={visitor} onErased={vi.fn()} onSignOut={vi.fn()} />);

    const field = await screen.findByLabelText("Name");
    await user.clear(field);
    await user.type(field, "Ada King");
    await user.click(screen.getByRole("button", { name: "Rename" }));

    await waitFor(() =>
      expect(calls.updateOwnName).toHaveBeenCalledWith("ada@example.org", "Ada King"),
    );
    expect(await screen.findByText("Saved")).toBeInTheDocument();
  });

  it("cannot submit a name that has not changed", async () => {
    render(<MyRecord visitor={visitor} onErased={vi.fn()} onSignOut={vi.fn()} />);
    expect(await screen.findByRole("button", { name: "Rename" })).toBeDisabled();
  });

  it("lets the server's name win over the device's copy", async () => {
    // Renamed in another tab, or by an operator, since this device last wrote
    // it down — the row is the truth, not localStorage.
    responses.record = { ok: true, data: record({ name: "Ada King" }) };
    render(<MyRecord visitor={visitor} onErased={vi.fn()} onSignOut={vi.fn()} />);

    await waitFor(() => expect(screen.getByLabelText("Name")).toHaveValue("Ada King"));
  });

  it("erases the row only after a confirmation", async () => {
    const user = userEvent.setup();
    const onErased = vi.fn();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<MyRecord visitor={visitor} onErased={onErased} onSignOut={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Erase my record" }));
    expect(calls.deleteOwn).not.toHaveBeenCalled();
    expect(onErased).not.toHaveBeenCalled();

    confirm.mockReturnValue(true);
    await user.click(screen.getByRole("button", { name: "Erase my record" }));

    await waitFor(() => expect(calls.deleteOwn).toHaveBeenCalledWith("ada@example.org"));
    // The row is gone, so the device must forget it too — otherwise the page
    // keeps rendering a record that no longer exists.
    expect(onErased).toHaveBeenCalledTimes(1);
    confirm.mockRestore();
  });

  it("renders a refusal rather than swallowing it", async () => {
    const user = userEvent.setup();
    responses.update = { ok: false, error: "invalid name" } as never;
    render(<MyRecord visitor={visitor} onErased={vi.fn()} onSignOut={vi.fn()} />);

    const field = await screen.findByLabelText("Name");
    await user.type(field, "!");
    await user.click(screen.getByRole("button", { name: "Rename" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("invalid name");
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });

  it("shows the admin marker without implying it granted anything", async () => {
    responses.record = { ok: true, data: record({ isAdmin: true }) };
    render(<MyRecord visitor={visitor} onErased={vi.fn()} onSignOut={vi.fn()} />);

    expect(await screen.findByText("admin marker")).toBeInTheDocument();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ActivityFeed } from "./ActivityFeed";

const calls = {
  adminEvents: vi.fn(),
  eventsMasked: vi.fn(),
  adminPurgeEvents: vi.fn(),
};
const responses = {
  admin: { ok: true, data: [event()] },
  masked: { ok: true, data: [event({ visitor: "a***@e***", sessionId: null, masked: true })] },
  purge: { ok: true, data: 17 },
};

function event(overrides: Record<string, unknown> = {}) {
  return {
    ts: "2026-08-11T09:00:00.000Z",
    event: "page_view",
    page: "/match",
    sessionId: "0f8e7d6c-aaaa-bbbb",
    visitor: "ada@example.org",
    masked: false,
    ...overrides,
  };
}

vi.mock("../../lib/site/stack", () => ({
  operatorToken: () => "held-token",
  adminEvents: (t: string) => {
    calls.adminEvents(t);
    return Promise.resolve(responses.admin);
  },
  eventsMasked: (e: string) => {
    calls.eventsMasked(e);
    return Promise.resolve(responses.masked);
  },
  adminPurgeEvents: (t: string, days: number) => {
    calls.adminPurgeEvents(t, days);
    return Promise.resolve(responses.purge);
  },
}));

describe("ActivityFeed", () => {
  beforeEach(() => {
    Object.values(calls).forEach((c) => c.mockClear());
    responses.admin = { ok: true, data: [event()] };
    responses.purge = { ok: true, data: 17 };
  });

  it("shows a signed-in visitor a masked feed with no retention control", async () => {
    render(<ActivityFeed email="ada@example.org" isOperator={false} onEventsChanged={vi.fn()} />);

    await waitFor(() => expect(calls.eventsMasked).toHaveBeenCalledWith("ada@example.org"));
    expect(await screen.findByText("a***@e***", { exact: false })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Purge" })).not.toBeInTheDocument();
  });

  it("shows an operator the address and session behind each event", async () => {
    render(<ActivityFeed email={null} isOperator onEventsChanged={vi.fn()} />);

    await waitFor(() => expect(calls.adminEvents).toHaveBeenCalledWith("held-token"));
    expect(await screen.findByText(/ada@example\.org/)).toBeInTheDocument();
    // Truncated to a recognisable prefix — the full session id is noise in a
    // dense list and identifies nothing on its own.
    expect(screen.getByText(/0f8e7d6c/)).toBeInTheDocument();
  });

  it("reads nothing for a visitor who has neither signed in nor unlocked", async () => {
    render(<ActivityFeed email={null} isOperator={false} onEventsChanged={vi.fn()} />);

    await screen.findByText("No telemetry events recorded yet.");
    expect(calls.eventsMasked).not.toHaveBeenCalled();
    expect(calls.adminEvents).not.toHaveBeenCalled();
  });

  it("purges by retention window after a confirmation, and reports the count", async () => {
    const user = userEvent.setup();
    const onEventsChanged = vi.fn();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ActivityFeed email={null} isOperator onEventsChanged={onEventsChanged} />);

    await user.click(await screen.findByRole("button", { name: "Purge" }));

    await waitFor(() => expect(calls.adminPurgeEvents).toHaveBeenCalledWith("held-token", 30));
    expect(await screen.findByText("Deleted 17 events.")).toBeInTheDocument();
    // The operator panel states a total that this just invalidated; leaving it
    // alone would have the page showing two different counts.
    expect(onEventsChanged).toHaveBeenCalledTimes(1);
    confirm.mockRestore();
  });

  it("reports a single deletion without pluralising it", async () => {
    const user = userEvent.setup();
    responses.purge = { ok: true, data: 1 };
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ActivityFeed email={null} isOperator onEventsChanged={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Purge" }));

    expect(await screen.findByText("Deleted 1 event.")).toBeInTheDocument();
    confirm.mockRestore();
  });

  it("does not purge when the confirmation is declined", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<ActivityFeed email={null} isOperator onEventsChanged={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Purge" }));

    expect(calls.adminPurgeEvents).not.toHaveBeenCalled();
    confirm.mockRestore();
  });

  it("honours a changed retention window", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ActivityFeed email={null} isOperator onEventsChanged={vi.fn()} />);

    const days = await screen.findByLabelText(/delete events older than/i);
    await user.clear(days);
    await user.type(days, "7");
    await user.click(screen.getByRole("button", { name: "Purge" }));

    await waitFor(() => expect(calls.adminPurgeEvents).toHaveBeenCalledWith("held-token", 7));
    confirm.mockRestore();
  });

  it("refuses a retention window that is not a number of days", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ActivityFeed email={null} isOperator onEventsChanged={vi.fn()} />);

    const days = await screen.findByLabelText(/delete events older than/i);
    await user.clear(days);
    await user.click(screen.getByRole("button", { name: "Purge" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/number of days/i);
    expect(calls.adminPurgeEvents).not.toHaveBeenCalled();
    confirm.mockRestore();
  });

  it("renders a failed read instead of an empty feed", async () => {
    responses.admin = { ok: false, error: "Could not reach the site layer." } as never;
    render(<ActivityFeed email={null} isOperator onEventsChanged={vi.fn()} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach");
  });
});

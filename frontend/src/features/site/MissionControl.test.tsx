import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MissionControl } from "./MissionControl";
import type { GateCopy, Visitor } from "../../lib/site/stack";

/**
 * The site layer is off by default, and Mission Control only renders when it
 * is on — so these tests pin the config to the enabled posture and drive the
 * client through mocks. What they are actually asserting is the entry rule:
 * arriving here without a visitor record puts the gate in front of you, and
 * which panels the page is composed of at each of the three tiers.
 */
vi.mock("../../lib/site/config", () => ({
  siteConfig: { enabled: true, url: "https://project.supabase.co", anonKey: "anon-key" },
  siteLayerEnabled: () => true,
}));

const TOKEN = "correct-horse-battery-staple";

const state: {
  visitor: Visitor | null;
  copy: GateCopy;
  token: string;
  eventTotal: number;
} = {
  visitor: null,
  copy: {
    enabled: true,
    title: "Sign in to Mission Control",
    body: "This site keeps a record of who visited.",
    fine: "Grants nothing in OHM.",
  },
  token: "",
  eventTotal: 4,
};
const signIn = vi.fn().mockResolvedValue(true);
const clearVisitor = vi.fn(() => {
  state.visitor = null;
});

/** The RPCs answer for the tier the caller actually holds, as the schema does. */
vi.mock("../../lib/site/stack", () => {
  const unauthorized = {
    ok: false as const,
    error: "That operator token was not accepted. Check it, or unlock again.",
  };
  const gated = <T,>(token: string, data: T) =>
    token === "correct-horse-battery-staple" ? { ok: true as const, data } : unauthorized;

  return {
    visitor: () => state.visitor,
    clearVisitor: () => clearVisitor(),
    gateCopy: () => Promise.resolve(state.copy),
    isOperator: () => Promise.resolve(state.token === TOKEN),
    track: vi.fn(),
    signIn: (name: string, email: string) => {
      state.visitor = { name, email };
      return signIn(name, email);
    },
    operatorToken: () => state.token,
    setOperatorToken: (t: string) => {
      state.token = t;
    },
    clearOperatorToken: () => {
      state.token = "";
    },
    adminStats: (t: string) => Promise.resolve(gated(t, state.eventTotal)),
    adminVisitors: (t: string) =>
      Promise.resolve(
        gated(t, [
          {
            name: "Ada Lovelace",
            email: "ada@example.org",
            masked: false,
            firstSeen: "2026-08-01T09:00:00.000Z",
            lastSeen: "2026-08-11T09:00:00.000Z",
            isAdmin: true,
          },
        ]),
      ),
    adminEvents: (t: string) =>
      Promise.resolve(
        gated(t, [
          {
            ts: "2026-08-11T09:00:00.000Z",
            event: "page_view",
            page: "/match",
            sessionId: "0f8e7d6c-aaaa",
            visitor: "ada@example.org",
            masked: false,
          },
        ]),
      ),
    adminUpdateVisitor: () => Promise.resolve({ ok: true, data: null }),
    adminDeleteVisitor: () => Promise.resolve({ ok: true, data: null }),
    adminPurgeEvents: () => {
      const deleted = state.eventTotal;
      state.eventTotal = 0;
      return Promise.resolve({ ok: true, data: deleted });
    },
    myRecord: (email: string) =>
      Promise.resolve({
        ok: true,
        data: {
          name: "Ada Lovelace",
          email,
          firstSeen: "2026-08-01T09:00:00.000Z",
          lastSeen: "2026-08-11T09:00:00.000Z",
          isAdmin: false,
        },
      }),
    updateOwnName: () => Promise.resolve({ ok: true, data: null }),
    deleteOwn: () => Promise.resolve({ ok: true, data: null }),
    visitorsMasked: () =>
      Promise.resolve({
        ok: true,
        data: [
          {
            name: "Ada Lovelace",
            email: "a***@e***",
            masked: true,
            firstSeen: null,
            lastSeen: "2026-08-11T09:00:00.000Z",
            isAdmin: false,
          },
        ],
      }),
    eventsMasked: () =>
      Promise.resolve({
        ok: true,
        data: [
          {
            ts: "2026-08-11T09:00:00.000Z",
            event: "page_view",
            page: "/match",
            sessionId: null,
            visitor: "a***@e***",
            masked: true,
          },
        ],
      }),
  };
});

function panel(name: string): HTMLElement {
  return screen.getByRole("region", { name: new RegExp(name, "i") });
}

describe("MissionControl", () => {
  beforeEach(() => {
    state.visitor = null;
    state.copy = { ...state.copy, enabled: true };
    state.token = "";
    state.eventTotal = 4;
    signIn.mockClear();
    clearVisitor.mockClear();
  });

  it("gates entry when no visitor record exists on this device", async () => {
    render(<MissionControl />);
    expect(
      await screen.findByRole("dialog", { name: "Sign in to Mission Control" }),
    ).toBeInTheDocument();
  });

  it("lets a returning visitor straight through to their record", async () => {
    state.visitor = { name: "Ada Lovelace", email: "ada@example.org" };
    render(<MissionControl />);

    expect(await screen.findByText("ada@example.org")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("respects an operator who turned the gate off", async () => {
    state.copy = { ...state.copy, enabled: false };
    render(<MissionControl />);

    expect(await screen.findByText("Not signed in")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    // No sign-in button either: the gate is the only way in, and it is off.
    expect(screen.queryByRole("button", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("shows the record once the gate is completed", async () => {
    const user = userEvent.setup();
    render(<MissionControl />);

    await screen.findByRole("dialog");
    await user.type(screen.getByLabelText("Name"), "Ada Lovelace");
    await user.type(screen.getByLabelText("Email"), "ada@example.org");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("ada@example.org")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("dismissal leaves a way back in rather than a dead end", async () => {
    const user = userEvent.setup();
    render(<MissionControl />);

    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "Not now" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(await screen.findByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("signing out forgets the record without re-gating the page", async () => {
    state.visitor = { name: "Ada Lovelace", email: "ada@example.org" };
    const user = userEvent.setup();
    render(<MissionControl />);

    await user.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(clearVisitor).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("Not signed in")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("offers the operator door to someone who has not signed in", async () => {
    state.copy = { ...state.copy, enabled: false };
    render(<MissionControl />);

    // Unlocking must not require a visitor record: the two tiers are separate
    // doors, and an operator on a fresh device goes straight to the token.
    expect(await screen.findByLabelText("Operator token")).toBeInTheDocument();
    // But the data surfaces stay closed until one of the doors opens.
    expect(screen.queryByRole("region", { name: /visitors/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /activity/i })).not.toBeInTheDocument();
  });

  it("gives a signed-in visitor the masked directory and feed", async () => {
    state.visitor = { name: "Ada Lovelace", email: "ada@example.org" };
    render(<MissionControl />);

    const visitors = await screen.findByRole("region", { name: /visitors/i });
    expect(within(visitors).getByText("masked")).toBeInTheDocument();
    expect(await within(visitors).findByText("a***@e***")).toBeInTheDocument();
    // The masked RPC does not return real addresses at all, so there is
    // nothing in this tier's DOM to un-mask.
    expect(within(visitors).queryByText("ada@example.org")).not.toBeInTheDocument();
    expect(
      within(visitors).queryByRole("button", { name: "Delete" }),
    ).not.toBeInTheDocument();
  });

  it("unlocking with the token swaps the masked reads for unmasked ones", async () => {
    const user = userEvent.setup();
    state.visitor = { name: "Ada Lovelace", email: "ada@example.org" };
    render(<MissionControl />);

    await user.type(await screen.findByLabelText("Operator token"), TOKEN);
    await user.click(screen.getByRole("button", { name: "Unlock" }));

    expect(await screen.findByText("verified")).toBeInTheDocument();
    const visitors = await screen.findByRole("region", { name: /visitors/i });
    expect(await within(visitors).findByText("ada@example.org")).toBeInTheDocument();
    expect(within(visitors).getByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(
      within(panel("activity")).getByRole("button", { name: "Purge" }),
    ).toBeInTheDocument();
  });

  it("refuses a wrong token and stays locked", async () => {
    const user = userEvent.setup();
    render(<MissionControl />);
    state.copy = { ...state.copy, enabled: false };

    await user.type(await screen.findByLabelText("Operator token"), "guess");
    await user.click(screen.getByRole("button", { name: "Unlock" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/not accepted/i);
    expect(screen.getByText("locked")).toBeInTheDocument();
    // Nothing was stored, so a later call cannot retry with a bad secret.
    expect(state.token).toBe("");
  });

  it("keeps the event total honest after a purge", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<MissionControl />);

    await user.type(await screen.findByLabelText("Operator token"), TOKEN);
    await user.click(screen.getByRole("button", { name: "Unlock" }));
    expect(await screen.findByText("4")).toBeInTheDocument();

    await user.click(within(panel("activity")).getByRole("button", { name: "Purge" }));

    // The count lives in a different panel from the control that invalidates
    // it; without the signal between them the page states 4 and 0 at once.
    expect(await screen.findByText("0")).toBeInTheDocument();
    confirm.mockRestore();
  });

  it("locking puts the unmasked surfaces away again", async () => {
    const user = userEvent.setup();
    state.visitor = { name: "Ada Lovelace", email: "ada@example.org" };
    render(<MissionControl />);

    await user.type(await screen.findByLabelText("Operator token"), TOKEN);
    await user.click(screen.getByRole("button", { name: "Unlock" }));
    await screen.findByText("verified");

    await user.click(screen.getByRole("button", { name: "Lock" }));

    expect(await screen.findByText("locked")).toBeInTheDocument();
    expect(state.token).toBe("");
    const visitors = await screen.findByRole("region", { name: /visitors/i });
    expect(await within(visitors).findByText("a***@e***")).toBeInTheDocument();
  });
});

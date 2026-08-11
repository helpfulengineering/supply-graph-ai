import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MissionControl } from "./MissionControl";
import type { GateCopy, Visitor } from "../../lib/site/stack";

/**
 * The site layer is off by default, and Mission Control only renders when it
 * is on — so these tests pin the config to the enabled posture and drive the
 * client through mocks. What they are actually asserting is the entry rule:
 * arriving here without a visitor record puts the gate in front of you.
 */
vi.mock("../../lib/site/config", () => ({
  siteConfig: { enabled: true, url: "https://project.supabase.co", anonKey: "anon-key" },
  siteLayerEnabled: () => true,
}));

const state: { visitor: Visitor | null; copy: GateCopy } = {
  visitor: null,
  copy: {
    enabled: true,
    title: "Sign in to Mission Control",
    body: "This site keeps a record of who visited.",
    fine: "Grants nothing in OHM.",
  },
};
const signIn = vi.fn().mockResolvedValue(true);
const clearVisitor = vi.fn(() => {
  state.visitor = null;
});

vi.mock("../../lib/site/stack", () => ({
  visitor: () => state.visitor,
  clearVisitor: () => clearVisitor(),
  gateCopy: () => Promise.resolve(state.copy),
  isOperator: () => Promise.resolve(false),
  track: vi.fn(),
  signIn: (name: string, email: string) => {
    state.visitor = { name, email };
    return signIn(name, email);
  },
}));

describe("MissionControl", () => {
  beforeEach(() => {
    state.visitor = null;
    state.copy = { ...state.copy, enabled: true };
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

    expect(await screen.findByText(/Ada Lovelace · ada@example.org/)).toBeInTheDocument();
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

    expect(await screen.findByText(/Ada Lovelace · ada@example.org/)).toBeInTheDocument();
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
});

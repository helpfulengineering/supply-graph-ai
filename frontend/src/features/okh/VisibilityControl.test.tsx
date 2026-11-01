import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VisibilityControl } from "./VisibilityControl";

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ hasWrite: true, reportAuthFailure: vi.fn() }),
}));
vi.mock("../../api/ohm/okh", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/ohm/okh")>();
  return {
    ...actual,
    getOkhVisibility: vi.fn(),
    setOkhVisibility: vi.fn(),
  };
});

import { getOkhVisibility, setOkhVisibility } from "../../api/ohm/okh";

function renderControl(kind: "okh" | "okw") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <VisibilityControl
        kind={kind}
        id={kind === "okh" ? "okh-0001" : "okw-1"}
      />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getOkhVisibility).mockResolvedValue({
    id: "okh-0001",
    visibility: "private",
  });
  vi.mocked(setOkhVisibility).mockImplementation(async (id, visibility) => ({
    id,
    visibility,
  }));
});

describe("VisibilityControl", () => {
  it.each(["okh", "okw"] as const)(
    "offers every level, narrowest first (%s)",
    async (kind) => {
      renderControl(kind);
      const select = await screen.findByLabelText("Visibility level");
      const options = Array.from(
        select.querySelectorAll("option"),
        (o) => o.value,
      );
      expect(options).toEqual(["private", "members", "followers", "public"]);
    },
  );
});

describe("VisibilityControl audience preview (#576)", () => {
  it("says who will see the record before anything changes", async () => {
    renderControl("okh");
    await userEvent.selectOptions(
      await screen.findByLabelText("Visibility level"),
      "followers",
    );

    expect(screen.getByText(/anyone visiting this node/i)).toBeInTheDocument();
    expect(screen.getByText(/nodes that follow this one/i)).toBeInTheDocument();
    expect(setOkhVisibility).not.toHaveBeenCalled();
  });

  it("applies the chosen level only when confirmed", async () => {
    renderControl("okh");
    await userEvent.selectOptions(
      await screen.findByLabelText("Visibility level"),
      "members",
    );
    await userEvent.click(screen.getByRole("button", { name: /apply/i }));

    expect(setOkhVisibility).toHaveBeenCalledWith("okh-0001", "members");
    expect(await screen.findByLabelText("Visibility level")).toHaveValue(
      "members",
    );
    expect(
      screen.queryByRole("button", { name: /apply/i }),
    ).not.toBeInTheDocument();
  });

  it("cancelling keeps the current level", async () => {
    renderControl("okh");
    const select = await screen.findByLabelText("Visibility level");
    await userEvent.selectOptions(select, "public");
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(select).toHaveValue("private");
    expect(screen.queryByText(/anyone who asks/i)).not.toBeInTheDocument();
    expect(setOkhVisibility).not.toHaveBeenCalled();
  });
});

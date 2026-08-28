import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import { mockRouter, setMockNavigation } from "../../test/nextNavigation";
import { OkwDetailView } from "./OkwDetailView";

const authState = { hasWrite: true };
const reportAuthFailure = vi.fn();

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    hasWrite: authState.hasWrite,
    reportAuthFailure,
  }),
}));

function renderDetail(path = "/facilities/okw-1") {
  const [pathname, search = ""] = path.split("?");
  setMockNavigation({ pathname, params: { id: "okw-1" }, search });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <OkwDetailView id="okw-1" />
    </QueryClientProvider>,
  );
}

describe("OkwDetailView slice 2", () => {
  beforeEach(() => {
    authState.hasWrite = true;
    reportAuthFailure.mockClear();
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("shows a dismissible post-create banner when ?created=1", async () => {
    const user = userEvent.setup();
    renderDetail("/facilities/okw-1?created=1");
    expect(await screen.findByText(/Facility created/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Edit facility/i }),
    ).toHaveAttribute("href", "/facilities/okw-1/edit");
    await user.click(screen.getByRole("button", { name: /Dismiss/i }));
    await waitFor(() => {
      expect(screen.queryByText(/Facility created/i)).not.toBeInTheDocument();
    });
  });

  it("deletes after confirm and redirects to the list", async () => {
    const user = userEvent.setup();
    let deleted = false;
    server.use(
      http.delete("*/v1/api/okw/:id", () => {
        deleted = true;
        return HttpResponse.json({ success: true, message: "deleted" });
      }),
    );
    renderDetail();
    await screen.findByRole("heading", { name: /Laser Fab Lab/i });
    await user.click(screen.getByRole("button", { name: /^Delete$/i }));
    await waitFor(() => {
      expect(deleted).toBe(true);
      expect(mockRouter.push).toHaveBeenCalledWith("/facilities");
    });
  });

  it("disables Delete when the user lacks write", async () => {
    authState.hasWrite = false;
    renderDetail();
    expect(
      await screen.findByRole("button", { name: /^Delete$/i }),
    ).toBeDisabled();
  });
});

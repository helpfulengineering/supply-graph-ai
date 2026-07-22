import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../test/msw/server";
import { DisclosureControl } from "./DisclosureControl";

const authState = { hasWrite: true };

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    hasWrite: authState.hasWrite,
    reportAuthFailure: vi.fn(),
  }),
}));

function renderControl(id = "okw-1") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <DisclosureControl id={id} />
    </QueryClientProvider>,
  );
}

describe("DisclosureControl", () => {
  beforeEach(() => {
    authState.hasWrite = true;
  });

  it("loads defaults and shows private export message", async () => {
    renderControl();
    expect(
      await screen.findByRole("heading", { name: /Sharing \/ disclosure/i }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/Nothing is exported while visibility is private/i),
    ).toBeInTheDocument();
    expect(document.getElementById("followers-identity")).toBeDisabled();
  });

  it("toggles a location group for followers", async () => {
    const user = userEvent.setup();
    renderControl();
    const location = await screen.findByLabelText(/Location/i, {
      selector: "#followers-location",
    });
    expect(location).not.toBeChecked();
    await user.click(location);
    await waitFor(() => {
      expect(location).toBeChecked();
    });
  });

  it("highlights active audience when visibility is followers", async () => {
    server.use(
      http.get("*/v1/api/okw/:id/visibility", () =>
        HttpResponse.json({ id: "okw-1", visibility: "followers" }),
      ),
      http.get("*/v1/api/okw/:id/disclosure/preview", () =>
        HttpResponse.json({
          id: "okw-1",
          audience: "followers",
          visibility: "followers",
          exported: true,
          groups: ["identity"],
          facility: { id: "okw-1", name: "Test Fab Lab", facility_status: "Active" },
        }),
      ),
    );
    renderControl();
    expect(await screen.findByText(/active for export/i)).toBeInTheDocument();
    expect(await screen.findByTestId("disclosure-preview-json")).toHaveTextContent(
      "Test Fab Lab",
    );
  });

  it("disables toggles when user lacks write", async () => {
    authState.hasWrite = false;
    renderControl();
    const location = await screen.findByLabelText(/Location/i, {
      selector: "#followers-location",
    });
    expect(location).toBeDisabled();
    expect(
      screen.getByText(/Changing disclosure requires a write-capable API key/i),
    ).toBeInTheDocument();
  });
});

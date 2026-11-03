import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/ohm/client";
import { server } from "../../test/msw/server";
import { mockRouter } from "../../test/nextNavigation";
import { CreateJsonRecordPage } from "./CreateJsonRecordPage";

const authState = { hasWrite: true };
const reportAuthFailure = vi.fn();

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    hasWrite: authState.hasWrite,
    reportAuthFailure,
  }),
}));

function renderPage(
  create: (
    content: Record<string, unknown>,
    opts: { author?: string; onBehalfOf?: string },
  ) => Promise<{ id: string }>,
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CreateJsonRecordPage
        title="New design"
        listHref="/designs"
        listLabel="Designs"
        detailHref={(id) => `/designs/${id}`}
        validate={async () => ({
          is_valid: true,
          score: 1,
          errors: [],
          warnings: [],
          suggestions: [],
        })}
        create={create}
        initialJson='{"title":"Bracket"}'
      />
    </QueryClientProvider>,
  );
}

describe("CreateJsonRecordPage", () => {
  beforeEach(() => {
    authState.hasWrite = true;
    reportAuthFailure.mockClear();
    mockRouter.push.mockClear();
  });

  it("offers affiliations and saves without one when the grant has lapsed", async () => {
    const user = userEvent.setup();
    const calls: Array<string | undefined> = [];
    server.use(
      http.get("*/v1/api/identity/affiliations", () =>
        HttpResponse.json([
          {
            space_did: "did:key:zFab",
            display_name: "FabLab",
            expires_at: "2026-12-01T00:00:00Z",
          },
        ]),
      ),
    );

    renderPage(async (_content, opts) => {
      calls.push(opts.onBehalfOf);
      if (calls.length === 1) {
        throw new ApiError(
          403,
          "You are not yet affiliated with that organisation. Attribution can be added later.",
        );
      }
      return { id: "okh-1" };
    });

    expect(
      await screen.findByRole("option", { name: "FabLab" }),
    ).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("space DID")).not.toBeInTheDocument();

    await user.selectOptions(
      screen.getByRole("combobox", { name: /on behalf of/i }),
      "did:key:zFab",
    );
    await user.click(screen.getByRole("button", { name: "Create" }));
    await user.click(
      await screen.findByRole("button", { name: /Save without organisation/i }),
    );

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith("/designs/okh-1");
    });
    expect(calls).toEqual(["did:key:zFab", undefined]);
  });
});

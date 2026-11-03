import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { AuthProvider } from "../../context/AuthContext";
import { MembersPanel } from "./MembersPanel";

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MembersPanel />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("MembersPanel", () => {
  it("names a member and their facility", async () => {
    server.use(
      http.get("*/v1/api/identity/members", () =>
        HttpResponse.json([
          {
            username: "ada",
            display_name: "Ada Lovelace",
            facilities: [
              {
                name: "Ada's printer",
                processes: ["3D Printing"],
                visibility: "members",
              },
            ],
          },
        ]),
      ),
    );

    renderPanel();

    expect(await screen.findByText(/Ada Lovelace/)).toBeInTheDocument();
    expect(screen.getByText(/Ada's printer/)).toBeInTheDocument();
    expect(screen.getByText("members")).toBeInTheDocument();
  });
});

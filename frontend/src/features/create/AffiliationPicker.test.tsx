import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { server } from "../../test/msw/server";
import { AffiliationPicker } from "./AffiliationPicker";

function Harness() {
  const [value, setValue] = useState("");
  return <AffiliationPicker value={value} onChange={setValue} />;
}

function renderPicker() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <Harness />
    </QueryClientProvider>,
  );
}

describe("AffiliationPicker", () => {
  it("selects the organisation when the caller has only one", async () => {
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
    renderPicker();
    expect(await screen.findByRole("option", { name: "FabLab" })).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /on behalf of/i })).toHaveValue(
        "did:key:zFab",
      ),
    );
  });

  it("leaves the choice open when the caller has several", async () => {
    server.use(
      http.get("*/v1/api/identity/affiliations", () =>
        HttpResponse.json([
          {
            space_did: "did:key:zFab",
            display_name: "FabLab",
            expires_at: "2026-12-01T00:00:00Z",
          },
          {
            space_did: "did:key:zOther",
            display_name: "Other Shop",
            expires_at: "2026-12-01T00:00:00Z",
          },
        ]),
      ),
    );
    renderPicker();
    expect(await screen.findByRole("option", { name: "Other Shop" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /on behalf of/i })).toHaveValue("");
  });
});

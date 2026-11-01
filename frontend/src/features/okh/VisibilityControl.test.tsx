import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VisibilityControl } from "./VisibilityControl";

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ hasWrite: true, reportAuthFailure: vi.fn() }),
}));

function renderControl(kind: "okh" | "okw") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <VisibilityControl kind={kind} id={kind === "okh" ? "okh-0001" : "okw-1"} />
    </QueryClientProvider>,
  );
}

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

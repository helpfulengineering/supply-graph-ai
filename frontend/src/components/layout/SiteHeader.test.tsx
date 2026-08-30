import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SiteHeader } from "./SiteHeader";
import { AuthProvider } from "../../context/AuthContext";
import { DomainContext } from "../../context/DomainContext";
import { setMockNavigation } from "../../test/nextNavigation";
import type { OhmDomain } from "../../features/settings/domainPreference";

/**
 * Generate is promoted out of the sitemap into the header.
 *
 * It is the longest-running and most distinctive operation in the product and
 * sat two clicks away behind an icon with no word on it. These tests pin the
 * three things that make the promotion correct rather than merely present.
 */
function renderHeader(domain: OhmDomain = "manufacturing") {
  // The header mounts the demo-data badge, which reads auth and the query
  // cache; the subject here is the Generate action, so those are supplied
  // rather than stubbed out.
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <DomainContext.Provider value={{ domain, setDomain: () => {} }}>
          <SiteHeader />
        </DomainContext.Provider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("SiteHeader — the Generate action", () => {
  it("is reachable by name, at every width", () => {
    // One text node, sr-only below `sm`, so the accessible name does not
    // depend on the viewport — the icon alone would leave the phone header
    // with an unnamed control.
    renderHeader();
    const action = screen.getByRole("link", { name: "Generate" });
    expect(action).toHaveAttribute("href", "/okh/generate");
  });

  it("does not claim the current page when you are elsewhere", () => {
    setMockNavigation({ pathname: "/okh" });
    renderHeader();
    expect(
      screen.getByRole("link", { name: "Generate" }),
    ).not.toHaveAttribute("aria-current");
  });

  it("claims the current page inside the generator", () => {
    setMockNavigation({ pathname: "/okh/generate" });
    renderHeader();
    expect(screen.getByRole("link", { name: "Generate" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("is absent in the cooking domain, which has no generator", () => {
    // navGroupsForDomain drops Generate for cooking. Promoting it anyway would
    // advertise in the chrome a route that domain deliberately removes.
    renderHeader("cooking");
    expect(
      screen.queryByRole("link", { name: "Generate" }),
    ).not.toBeInTheDocument();
  });

  it("leaves the existing header controls alone", () => {
    renderHeader();
    expect(screen.getByRole("button", { name: /Switch to/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Site menu" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Open Hardware Manager/ }),
    ).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PageHero } from "./PageHero";

/**
 * The hero crumb, as a contract rather than as markup each view rebuilds.
 *
 * The crumb used to be a string every view wrote out, so linking a term meant
 * hand-rolling anchors and separators in that view — which is how the dashboard
 * ended up as the only place the terms went anywhere. These assert the shape
 * PageHero guarantees to all of them.
 */
describe("PageHero crumb", () => {
  it("renders a plain string unchanged", () => {
    render(<PageHero title="Network" crumb="local · federated · filtered" />);
    expect(
      screen.getByText("local · federated · filtered"),
    ).toBeInTheDocument();
  });

  it("links the terms that name a destination and leaves the rest as text", () => {
    render(
      <PageHero
        title="Open Hardware Designs"
        crumb={[
          { label: "catalog" },
          { label: "facets" },
          { label: "matching", href: "/match" },
        ]}
      />,
    );

    expect(screen.getByRole("link", { name: "matching" })).toHaveAttribute(
      "href",
      "/match",
    );
    // A term with no honest destination stays text. Linking it somewhere
    // approximate is worse than not linking it.
    expect(screen.queryByRole("link", { name: "catalog" })).toBeNull();
    expect(screen.queryByRole("link", { name: "facets" })).toBeNull();
  });

  /**
   * The separators are the reason this component exists rather than a map in
   * each view. WCAG 2.5.8 exempts a target rendered inline within text, and
   * responsive.spec.ts implements that exemption literally: it requires the
   * link's parent to be neither flex nor grid and to carry text besides the
   * link itself. Emit the separators as wrappers, or give each term its own
   * row, and every crumb link in the app becomes a standalone target required
   * to reach 24px — which caption scale cannot do without breaking the line
   * box. So the flat structure is load-bearing, and asserted here.
   */
  it("keeps every term in one parent, separated by text nodes", () => {
    render(
      <PageHero
        title="Open Hardware Manager"
        crumb={[
          { label: "designs", href: "/okh" },
          { label: "facilities", href: "/facilities" },
          { label: "supply chains", href: "/match" },
        ]}
      />,
    );

    const link = screen.getByRole("link", { name: "designs" });
    const parent = link.parentElement;
    expect(parent).not.toBeNull();

    // All three links are siblings under the same span...
    for (const label of ["facilities", "supply chains"]) {
      expect(screen.getByRole("link", { name: label }).parentElement).toBe(
        parent,
      );
    }
    // ...and that span carries the separators as its own text, which is what
    // "inline within text" means to the audit.
    expect(parent?.textContent).toBe("designs · facilities · supply chains");
    expect(parent?.querySelector("ul, ol, li")).toBeNull();
  });
});

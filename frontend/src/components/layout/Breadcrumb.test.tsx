import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Breadcrumb } from "./Breadcrumb";

/**
 * The trail's contract, which four hand-written copies had each got partly
 * wrong. jsdom cannot measure the 24px target — that is asserted against a real
 * layout in e2e/breadcrumb.spec.ts — but everything semantic lives here.
 */
describe("Breadcrumb", () => {
  const trail = [
    { label: "Facilities", href: "/facilities" },
    { label: "Laser Fab Lab" },
  ];

  it("names its landmark", () => {
    render(<Breadcrumb trail={trail} />);
    // Three of the four hand-rolled trails were a bare <nav>, so a screen
    // reader listing landmarks found an unnamed navigation region on every
    // detail page in the app.
    expect(
      screen.getByRole("navigation", { name: "Breadcrumb" }),
    ).toBeInTheDocument();
  });

  it("links the ancestors and marks the leaf as the current page", () => {
    render(<Breadcrumb trail={trail} />);

    expect(screen.getByRole("link", { name: "Facilities" })).toHaveAttribute(
      "href",
      "/facilities",
    );
    // The page you are on is not a link to itself.
    expect(screen.queryByRole("link", { name: "Laser Fab Lab" })).toBeNull();

    const leaf = screen.getByText("Laser Fab Lab");
    expect(leaf).toHaveAttribute("aria-current", "page");
  });

  it("hides the separators from assistive technology", () => {
    const { container } = render(<Breadcrumb trail={trail} />);
    // "Facilities › Laser Fab Lab" read aloud with the chevron is noise; the
    // trail's structure is already carried by the landmark and aria-current.
    const separators = container.querySelectorAll('[aria-hidden="true"]');
    expect(separators).toHaveLength(1);
    expect(separators[0].textContent).toBe("›");
  });

  it("renders a trail of one without a leading separator", () => {
    const { container } = render(
      <Breadcrumb trail={[{ label: "Packages" }]} />,
    );
    expect(container.querySelector('[aria-hidden="true"]')).toBeNull();
  });
});

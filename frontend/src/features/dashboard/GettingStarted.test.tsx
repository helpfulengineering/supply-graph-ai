import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GettingStarted } from "./GettingStarted";

describe("GettingStarted", () => {
  it("offers adding a design, not only finding one (#561)", () => {
    render(<GettingStarted />);

    expect(screen.getByRole("link", { name: /add your design/i })).toHaveAttribute(
      "href",
      "/okh/generate",
    );
    expect(screen.getByRole("link", { name: /for designers/i })).toHaveAttribute(
      "href",
      "/docs/guides/for-designers/",
    );
  });

  it("keeps the path for people looking for something to build", () => {
    render(<GettingStarted />);

    expect(screen.getByRole("link", { name: /browse designs/i })).toHaveAttribute(
      "href",
      "/okh",
    );
  });
});

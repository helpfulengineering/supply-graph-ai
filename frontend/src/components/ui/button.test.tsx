import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./button";

// Component-layer smoke: proves Testing Library renders the pinned shadcn/ui
// vocabulary and that user interaction wiring works.
describe("harness: component (shadcn Button)", () => {
  it("renders its label", () => {
    render(<Button>Run match</Button>);
    expect(screen.getByRole("button", { name: "Run match" })).toBeInTheDocument();
  });

  it("fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).toHaveBeenCalledOnce();
  });
});

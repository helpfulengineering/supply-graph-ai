import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmptyState, ErrorState, LoadingState } from "./states";

describe("state primitives", () => {
  it("LoadingState exposes a status role and message", () => {
    render(<LoadingState message="Loading designs…" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading designs…");
  });

  it("EmptyState renders title, description, and action", () => {
    render(
      <EmptyState
        title="No designs found"
        description="Try a different search."
        action={<button>Clear</button>}
      />,
    );
    expect(screen.getByText("No designs found")).toBeInTheDocument();
    expect(screen.getByText("Try a different search.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear" })).toBeInTheDocument();
  });

  it("ErrorState exposes an alert role and fires onRetry", async () => {
    const onRetry = vi.fn();
    render(<ErrorState description="Network error" onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("ErrorState omits the retry button when no handler is given", () => {
    render(<ErrorState description="Network error" />);
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });
});

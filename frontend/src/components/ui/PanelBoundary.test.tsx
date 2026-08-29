import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { PanelBoundary } from "./PanelBoundary";

function Throws(): never {
  throw new Error("bad payload shape");
}

describe("PanelBoundary", () => {
  beforeEach(() => {
    // React logs the caught error itself; the boundary logs it again on
    // purpose. Neither is a test failure, and both are noise here.
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders its children when nothing throws", () => {
    render(
      <PanelBoundary label="Components">
        <p>the panel</p>
      </PanelBoundary>,
    );
    expect(screen.getByText("the panel")).toBeInTheDocument();
  });

  it("names the failed panel and leaves its siblings standing", () => {
    render(
      <div>
        <p>the graph</p>
        <PanelBoundary label="Components">
          <Throws />
        </PanelBoundary>
      </div>,
    );
    expect(screen.getByText("Components")).toBeInTheDocument();
    expect(screen.getByText(/could not be displayed/i)).toBeInTheDocument();
    // The whole point: a panel costs a panel, not the view.
    expect(screen.getByText("the graph")).toBeInTheDocument();
  });
});

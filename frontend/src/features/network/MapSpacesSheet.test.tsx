import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { NetworkSpace } from "../../api/ohm/network";
import { MapSpacesSheet } from "./MapSpacesSheet";

function space(overrides: Partial<NetworkSpace>): NetworkSpace {
  return {
    id: "s1",
    name: "A space",
    source: "mom",
    lat: 0,
    lon: 0,
    city: null,
    region: null,
    country: null,
    status: null,
    access_type: null,
    url: "https://example.org",
    ambiguous: false,
    processes: [],
    ...overrides,
  };
}

const BERLIN = [
  space({ id: "1", name: "Berlin Offene Werkstatt", city: "Berlin" }),
  space({ id: "2", name: "schokowerkstatt", city: "Berlin" }),
];

describe("MapSpacesSheet", () => {
  it("draws nothing until it is opened", () => {
    render(<MapSpacesSheet spaces={BERLIN} open={false} onClose={() => {}} />);
    const sheet = screen.getByLabelText("Spaces in view");
    expect(sheet).toHaveAttribute("aria-hidden", "true");
    expect(screen.queryByText("schokowerkstatt")).not.toBeInTheDocument();
  });

  it("names the region and its spaces when open", () => {
    render(<MapSpacesSheet spaces={BERLIN} open onClose={() => {}} />);
    expect(screen.getByText("2 spaces in view")).toBeInTheDocument();
    expect(screen.getByText("Berlin Offene Werkstatt")).toBeInTheDocument();
    expect(screen.getByText("schokowerkstatt")).toBeInTheDocument();
  });

  it("says so when the frame holds nothing", () => {
    render(<MapSpacesSheet spaces={[]} open onClose={() => {}} />);
    expect(screen.getByText("Nothing in view")).toBeInTheDocument();
    expect(screen.getByText(/Pan or zoom out/)).toBeInTheDocument();
  });

  it("closes on the button and on Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<MapSpacesSheet spaces={BERLIN} open onClose={onClose} />);

    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("caps the cards it draws and says what it left out", () => {
    const many = Array.from({ length: 30 }, (_, i) =>
      space({ id: `x${i}`, name: `Space ${i}` }),
    );
    render(<MapSpacesSheet spaces={many} open onClose={() => {}} />);

    expect(screen.getByText("30 spaces in view")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(24);
    expect(screen.getByText(/Showing 24 of 30/)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "browse them all" }),
    ).toHaveAttribute("href", "/facilities?view=map");
  });
});

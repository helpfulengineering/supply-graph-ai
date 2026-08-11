import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { NetworkBarChart } from "./NetworkBarChart";

/**
 * The card survives having nothing to chart.
 *
 * It used to `return null`, and on the dashboard these two charts sit in a
 * two-column grid — so an instance whose facilities carry no manufacturing
 * processes (a fresh one, and the seeded demo world) lost "What it can make"
 * entirely and showed one card beside an empty column. A card that deletes
 * itself cannot be read as "nothing yet"; it reads as something broken, or as
 * nothing having been there at all.
 */

// echarts renders to SVG through a canvas-measuring layout pass jsdom does not
// implement, and none of these assertions are about the chart itself.
vi.mock("echarts-for-react", () => ({
  default: () => <div data-testid="chart" />,
}));

// jsdom implements no matchMedia, and the chart narrows its axis labels off
// one. Desktop is the width these assertions describe.
beforeAll(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    onchange: null,
    dispatchEvent: () => false,
  }));
});

const ROWS = [
  { key: "us", label: "United States", value: 2 },
  { key: "de", label: "Germany", value: 1 },
];

describe("NetworkBarChart", () => {
  it("keeps its heading and says why when there is nothing to chart", () => {
    render(
      <NetworkBarChart
        title="What it can make"
        caption="Facilities offering each capability"
        rows={[]}
        noun="capabilities"
        empty="These facilities list no manufacturing processes yet."
      />,
    );

    // The card is still on the page, still labelled, still findable.
    expect(
      screen.getByRole("region", { name: "What it can make" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("These facilities list no manufacturing processes yet."),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("chart")).toBeNull();
  });

  it("draws the chart when there are rows", () => {
    render(
      <NetworkBarChart
        title="Where the network is"
        caption="Facilities by country"
        rows={ROWS}
        noun="countries"
        empty="unused"
      />,
    );

    expect(screen.getByTestId("chart")).toBeInTheDocument();
    expect(screen.queryByText("unused")).toBeNull();
  });
});

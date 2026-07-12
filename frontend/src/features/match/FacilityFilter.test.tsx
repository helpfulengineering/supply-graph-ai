import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FacilityFilter, facilityPassesGeo, type FacilityOption } from "./FacilityFilter";

const facilities: FacilityOption[] = [
  {
    id: "okw-1",
    name: "Laser Fab Lab",
    city: "Austin",
    region: "TX",
    country: "US",
    source: "local",
  },
  {
    id: "okw-2",
    name: "Community Makerspace",
    city: "Austin",
    region: "TX",
    country: "US",
    source: "local",
  },
  {
    id: "urn:mak:space/lazio",
    name: "FabLab Lazio Roma",
    city: "Rome",
    region: "Lazio",
    country: "IT",
    source: "mom",
  },
];

describe("facilityPassesGeo", () => {
  it("matches full country/region names against codes", () => {
    expect(
      facilityPassesGeo(facilities[0], {
        source: "",
        country: "United States",
        region: "Texas",
        city: "",
      }),
    ).toBe(true);
    expect(
      facilityPassesGeo(facilities[2], {
        source: "",
        country: "",
        region: "Texas",
        city: "",
      }),
    ).toBe(false);
  });

  it("filters by network source", () => {
    expect(
      facilityPassesGeo(facilities[2], {
        source: "mom",
        country: "",
        region: "",
        city: "",
      }),
    ).toBe(true);
    expect(
      facilityPassesGeo(facilities[0], {
        source: "mom",
        country: "",
        region: "",
        city: "",
      }),
    ).toBe(false);
  });
});

describe("FacilityFilter", () => {
  it("is expanded by default with source and geo filters visible", () => {
    render(
      <FacilityFilter facilities={facilities} selectedIds={[]} onChange={() => {}} />,
    );
    expect(screen.getByLabelText("Source")).toBeInTheDocument();
    expect(screen.getByLabelText("Country")).toBeInTheDocument();
    expect(screen.getByLabelText("State / Region")).toBeInTheDocument();
    expect(screen.getByLabelText("City")).toBeInTheDocument();
    expect(screen.queryByLabelText("State")).not.toBeInTheDocument();
    expect(screen.getByText(/select facilities to match against/i)).toBeInTheDocument();
    expect(screen.getByLabelText("FabLab Lazio Roma")).toBeInTheDocument();
  });

  it("shows full country and state/region names in options", () => {
    render(
      <FacilityFilter facilities={facilities} selectedIds={[]} onChange={() => {}} />,
    );
    const country = screen.getByLabelText("Country");
    expect(country).toContainHTML("United States");
    expect(country).toContainHTML("Italy");
    const region = screen.getByLabelText("State / Region");
    expect(region).toContainHTML("Texas");
    expect(region).toContainHTML("Lazio");
  });

  it("narrows to Maps of Making via Source and clears conflicting geo filters", async () => {
    render(
      <FacilityFilter facilities={facilities} selectedIds={[]} onChange={() => {}} />,
    );
    await userEvent.selectOptions(screen.getByLabelText("City"), "Austin");
    expect(screen.queryByLabelText("FabLab Lazio Roma")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Source"), "mom");
    // Source change clears City so MoM spaces are visible again.
    expect(screen.getByLabelText("City")).toHaveValue("");
    expect(screen.getByLabelText("FabLab Lazio Roma")).toBeInTheDocument();
    expect(screen.queryByLabelText("Laser Fab Lab")).not.toBeInTheDocument();
  });

  it("toggling a facility reports the new selection", async () => {
    const onChange = vi.fn();
    render(
      <FacilityFilter facilities={facilities} selectedIds={[]} onChange={onChange} />,
    );
    await userEvent.click(screen.getByLabelText("FabLab Lazio Roma"));
    expect(onChange).toHaveBeenCalledWith(["urn:mak:space/lazio"]);
  });

  it("select all visible reports filtered ids; clear empties it", async () => {
    const onChange = vi.fn();
    render(
      <FacilityFilter facilities={facilities} selectedIds={["okw-1"]} onChange={onChange} />,
    );
    await userEvent.selectOptions(screen.getByLabelText("Source"), "local");
    await userEvent.click(screen.getByRole("button", { name: /select all visible/i }));
    expect(onChange).toHaveBeenLastCalledWith(["okw-1", "okw-2"]);
    await userEvent.click(screen.getByRole("button", { name: /clear/i }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});

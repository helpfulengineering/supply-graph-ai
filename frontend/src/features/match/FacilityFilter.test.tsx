import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  FacilityFilter,
  facilityPassesGeo,
  type FacilityOption,
} from "./FacilityFilter";

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
      <FacilityFilter
        facilities={facilities}
        selectedIds={[]}
        onChange={() => {}}
      />,
    );
    expect(screen.getByLabelText("Source")).toBeInTheDocument();
    expect(screen.getByLabelText("Country")).toBeInTheDocument();
    expect(screen.getByLabelText("State / Region")).toBeInTheDocument();
    expect(screen.getByLabelText("City")).toBeInTheDocument();
    expect(screen.queryByLabelText("State")).not.toBeInTheDocument();
    expect(
      screen.getByText(/select facilities to match against/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^FabLab Lazio Roma\b/)).toBeInTheDocument();
  });

  it("shows full country and state/region names in options", () => {
    render(
      <FacilityFilter
        facilities={facilities}
        selectedIds={[]}
        onChange={() => {}}
      />,
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
      <FacilityFilter
        facilities={facilities}
        selectedIds={[]}
        onChange={() => {}}
      />,
    );
    await userEvent.selectOptions(screen.getByLabelText("City"), "Austin");
    expect(
      screen.queryByLabelText(/^FabLab Lazio Roma\b/),
    ).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Source"), "mom");
    // Source change clears City so MoM spaces are visible again.
    expect(screen.getByLabelText("City")).toHaveValue("");
    expect(screen.getByLabelText(/^FabLab Lazio Roma\b/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Laser Fab Lab\b/)).not.toBeInTheDocument();
  });

  it("toggling a facility reports the new selection", async () => {
    const onChange = vi.fn();
    render(
      <FacilityFilter
        facilities={facilities}
        selectedIds={[]}
        onChange={onChange}
      />,
    );
    await userEvent.click(screen.getByLabelText(/^FabLab Lazio Roma\b/));
    expect(onChange).toHaveBeenCalledWith(["urn:mak:space/lazio"]);
  });

  it("select all visible reports filtered ids; clear empties it", async () => {
    const onChange = vi.fn();
    render(
      <FacilityFilter
        facilities={facilities}
        selectedIds={["okw-1"]}
        onChange={onChange}
      />,
    );
    await userEvent.selectOptions(screen.getByLabelText("Source"), "local");
    await userEvent.click(
      screen.getByRole("button", { name: /select all visible/i }),
    );
    expect(onChange).toHaveBeenLastCalledWith(["okw-1", "okw-2"]);
    await userEvent.click(screen.getByRole("button", { name: /clear/i }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});

describe("city options", () => {
  const messy: FacilityOption[] = [
    {
      id: "a",
      name: "A",
      city: "1050 Wien",
      region: null,
      country: "AT",
      source: "mom",
    },
    {
      id: "b",
      name: "B",
      city: "1070 Wien",
      region: null,
      country: "AT",
      source: "mom",
    },
    {
      id: "c",
      name: "C",
      city: "-- .",
      region: null,
      country: "AT",
      source: "mom",
    },
    {
      id: "d",
      name: "D",
      city: "Apenrader Str. 49",
      region: null,
      country: "DE",
      source: "mom",
    },
    {
      id: "e",
      name: "E",
      city: "Berlin",
      region: null,
      country: "DE",
      source: "mom",
    },
  ];

  function cityNames() {
    const select = screen.getByLabelText("City") as HTMLSelectElement;
    return [...select.options]
      .map((o) => o.text)
      .filter((t) => t !== "All cities");
  }

  it("drops artifacts and merges postal-code variants", () => {
    render(
      <FacilityFilter facilities={messy} selectedIds={[]} onChange={vi.fn()} />,
    );
    const names = cityNames();
    expect(names).toContain("Wien");
    expect(names).toContain("Berlin");
    // One Vienna, not two.
    expect(names.filter((n) => n === "Wien")).toHaveLength(1);
    expect(names).not.toContain("-- .");
    expect(names).not.toContain("Apenrader Str. 49");
  });

  it("constrains cities to the selected country", async () => {
    render(
      <FacilityFilter facilities={messy} selectedIds={[]} onChange={vi.fn()} />,
    );
    expect(cityNames()).toContain("Berlin");

    await userEvent.selectOptions(screen.getByLabelText("Country"), "Austria");

    // Cities outside the chosen country are unselectable anyway — the geo
    // filters are AND-ed — so offering them is noise.
    expect(cityNames()).toContain("Wien");
    expect(cityNames()).not.toContain("Berlin");
  });
});

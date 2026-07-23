import { describe, expect, it } from "vitest";
import {
  emptyFacilityForm,
  facilityToForm,
  formClientErrors,
  formToOkwContent,
  importJsonToForm,
  resolveManufacturingProcesses,
  type TaxonomyProcess,
} from "./facilityFormModel";

const TAXONOMY: TaxonomyProcess[] = [
  { canonical_id: "3d_printing", display_name: "3D Printing", parent: null, children: ["3d_printing_fdm"] },
  {
    canonical_id: "3d_printing_fdm",
    display_name: "FDM 3D Printing",
    parent: "3d_printing",
    children: [],
  },
  { canonical_id: "cnc_machining", display_name: "CNC Machining", parent: null, children: ["cnc_milling"] },
  { canonical_id: "cnc_milling", display_name: "CNC Milling", parent: "cnc_machining", children: [] },
];

describe("resolveManufacturingProcesses", () => {
  it("stores parent ids when no subtypes selected", () => {
    expect(
      resolveManufacturingProcesses(["3d_printing", "cnc_machining"], [], TAXONOMY),
    ).toEqual(["3d_printing", "cnc_machining"]);
  });

  it("prefers subtypes over parent when subtypes are selected", () => {
    expect(
      resolveManufacturingProcesses(["3d_printing"], ["3d_printing_fdm"], TAXONOMY),
    ).toEqual(["3d_printing_fdm"]);
  });
});

describe("formToOkwContent", () => {
  it("maps useful fields and omits empty equipment stubs", () => {
    const state = emptyFacilityForm();
    state.name = "Test Lab";
    state.city = "Boston";
    state.country = "US";
    state.facilityStatus = "Active";
    state.accessType = "Restricted";
    state.selectedParents = ["3d_printing"];
    state.equipment = [
      { processId: "3d_printing", make: "", model: "" },
      { processId: "3d_printing", make: "Prusa", model: "MK4" },
    ];

    const content = formToOkwContent(state, TAXONOMY);
    expect(content.name).toBe("Test Lab");
    expect(content.facility_status).toBe("Active");
    expect(content.access_type).toBe("Restricted");
    expect(content.manufacturing_processes).toEqual(["3d_printing"]);
    expect(content.location).toMatchObject({
      city: "Boston",
      country: "US",
      address: { city: "Boston", country: "US" },
    });
    expect(content.equipment).toEqual([
      {
        equipment_type: "3d_printing",
        manufacturing_process: "3d_printing",
        make: "Prusa",
        model: "MK4",
      },
    ]);
  });

  it("includes hours and contact when set", () => {
    const state = emptyFacilityForm();
    state.name = "Lab";
    state.city = "X";
    state.country = "US";
    state.openingHours = "9-5";
    state.contactEmail = "a@b.c";
    const content = formToOkwContent(state, TAXONOMY);
    expect(content.opening_hours).toBe("9-5");
    expect(content.contact).toMatchObject({ email: "a@b.c" });
  });
});

describe("formClientErrors", () => {
  it("requires name, city, and country", () => {
    const errs = formClientErrors(emptyFacilityForm());
    expect(errs).toEqual(
      expect.arrayContaining(["Name is required", "City is required", "Country is required"]),
    );
  });
});

describe("facilityToForm / importJsonToForm", () => {
  it("round-trips core fields from a facility payload", () => {
    const form = facilityToForm(
      {
        id: "okw-1",
        name: "Laser Fab Lab",
        facility_status: "Active",
        access_type: "Membership",
        description: "A lab",
        location: { city: "Austin", country: "US", address: { city: "Austin", country: "US" } },
        manufacturing_processes: ["3d_printing_fdm", "cnc_machining"],
        equipment: [{ manufacturing_process: "cnc_machining", make: "Haas", model: "VF-2" }],
        opening_hours: "10-6",
      },
      TAXONOMY,
    );
    expect(form.name).toBe("Laser Fab Lab");
    expect(form.selectedSubtypes).toContain("3d_printing_fdm");
    expect(form.selectedParents).toContain("3d_printing");
    expect(form.selectedParents).toContain("cnc_machining");
    expect(form.equipment).toEqual([
      { processId: "cnc_machining", make: "Haas", model: "VF-2" },
    ]);
  });

  it("imports JSON object into form state", () => {
    const { form, error } = importJsonToForm(
      JSON.stringify({
        name: "Imported",
        facility_status: "Planned",
        access_type: "Public",
        location: { address: { city: "Berlin", country: "DE" } },
        manufacturing_processes: ["cnc_milling"],
      }),
      TAXONOMY,
    );
    expect(error).toBeNull();
    expect(form?.name).toBe("Imported");
    expect(form?.selectedSubtypes).toContain("cnc_milling");
    expect(form?.selectedParents).toContain("cnc_machining");
  });
});

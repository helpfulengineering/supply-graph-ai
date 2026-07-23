/** Pure form state ↔ OKW payload mapping for facility create/edit. */

export type FacilityStatus = "Active" | "Planned" | "Temporary Closure" | "Closed";
export type AccessType =
  | "Restricted"
  | "Restricted with public hours"
  | "Shared space"
  | "Public"
  | "Membership";

export const FACILITY_STATUSES: FacilityStatus[] = [
  "Active",
  "Planned",
  "Temporary Closure",
  "Closed",
];

export const ACCESS_TYPES: AccessType[] = [
  "Restricted",
  "Restricted with public hours",
  "Shared space",
  "Public",
  "Membership",
];

export interface TaxonomyProcess {
  canonical_id: string;
  display_name: string;
  parent: string | null;
  children: string[];
}

export interface EquipmentRow {
  processId: string;
  make: string;
  model: string;
}

export interface FacilityFormState {
  name: string;
  facilityStatus: FacilityStatus;
  accessType: AccessType;
  description: string;
  city: string;
  region: string;
  country: string;
  street: string;
  selectedParents: string[];
  selectedSubtypes: string[];
  openingHours: string;
  contactEmail: string;
  contactPhone: string;
  contactUrl: string;
  equipment: EquipmentRow[];
  author: string;
  onBehalfOf: string;
}

export function emptyFacilityForm(): FacilityFormState {
  return {
    name: "",
    facilityStatus: "Active",
    accessType: "Restricted",
    description: "",
    city: "",
    region: "",
    country: "",
    street: "",
    selectedParents: [],
    selectedSubtypes: [],
    openingHours: "",
    contactEmail: "",
    contactPhone: "",
    contactUrl: "",
    equipment: [],
    author: "",
    onBehalfOf: "",
  };
}

/** Parents with no selected children → parent id; else selected children only. */
export function resolveManufacturingProcesses(
  selectedParents: string[],
  selectedSubtypes: string[],
  taxonomy: TaxonomyProcess[],
): string[] {
  const byId = new Map(taxonomy.map((p) => [p.canonical_id, p]));
  const out = new Set<string>();

  for (const parentId of selectedParents) {
    const parent = byId.get(parentId);
    const childIds = parent?.children ?? [];
    const chosenKids = childIds.filter((c) => selectedSubtypes.includes(c));
    if (chosenKids.length > 0) {
      for (const c of chosenKids) out.add(c);
    } else {
      out.add(parentId);
    }
  }

  // Subtypes selected without their parent still count
  for (const sub of selectedSubtypes) {
    const node = byId.get(sub);
    if (!node?.parent || !selectedParents.includes(node.parent)) {
      out.add(sub);
    }
  }

  return Array.from(out).sort();
}

function asStatus(raw: unknown): FacilityStatus {
  return FACILITY_STATUSES.includes(raw as FacilityStatus)
    ? (raw as FacilityStatus)
    : "Active";
}

function asAccess(raw: unknown): AccessType {
  return ACCESS_TYPES.includes(raw as AccessType) ? (raw as AccessType) : "Restricted";
}

export function formClientErrors(state: FacilityFormState): string[] {
  const errs: string[] = [];
  if (!state.name.trim()) errs.push("Name is required");
  if (!state.city.trim()) errs.push("City is required");
  if (!state.country.trim()) errs.push("Country is required");
  return errs;
}

export function formToOkwContent(
  state: FacilityFormState,
  taxonomy: TaxonomyProcess[],
): Record<string, unknown> {
  const processes = resolveManufacturingProcesses(
    state.selectedParents,
    state.selectedSubtypes,
    taxonomy,
  );
  const equipment = state.equipment
    .filter((e) => e.make.trim() || e.model.trim())
    .map((e) => ({
      equipment_type: e.processId || "equipment",
      manufacturing_process: e.processId || "equipment",
      make: e.make.trim() || undefined,
      model: e.model.trim() || undefined,
    }));

  const city = state.city.trim();
  const country = state.country.trim();
  const region = state.region.trim();
  const street = state.street.trim();
  const address: Record<string, string> = { city, country };
  if (region) address.region = region;
  if (street) address.street = street;

  const content: Record<string, unknown> = {
    name: state.name.trim(),
    facility_status: state.facilityStatus,
    access_type: state.accessType,
    location: {
      city,
      country,
      ...(region ? { region } : {}),
      address,
    },
    manufacturing_processes: processes,
  };

  if (state.description.trim()) content.description = state.description.trim();
  if (state.openingHours.trim()) content.opening_hours = state.openingHours.trim();

  const contact: Record<string, string> = {};
  if (state.contactEmail.trim()) contact.email = state.contactEmail.trim();
  if (state.contactPhone.trim()) contact.phone = state.contactPhone.trim();
  if (state.contactUrl.trim()) contact.url = state.contactUrl.trim();
  if (Object.keys(contact).length) content.contact = contact;

  if (equipment.length) content.equipment = equipment;

  return content;
}

/** Body for PUT /api/okw/{id} (flat update request). */
export function formToUpdateBody(
  state: FacilityFormState,
  taxonomy: TaxonomyProcess[],
): Record<string, unknown> {
  const content = formToOkwContent(state, taxonomy);
  return {
    name: content.name,
    location: content.location,
    facility_status: content.facility_status,
    access_type: content.access_type,
    description: content.description ?? null,
    opening_hours: content.opening_hours ?? null,
    contact: content.contact ?? null,
    manufacturing_processes: content.manufacturing_processes ?? [],
    equipment: content.equipment ?? [],
  };
}

type LooseFacility = {
  id?: string;
  name?: string;
  facility_status?: string | null;
  access_type?: string | null;
  description?: string | null;
  opening_hours?: string | null;
  location?: {
    city?: string | null;
    country?: string | null;
    region?: string | null;
    address?: {
      city?: string | null;
      country?: string | null;
      region?: string | null;
      street?: string | null;
    } | null;
  } | null;
  manufacturing_processes?: string[];
  equipment?: Array<{
    manufacturing_process?: string | null;
    equipment_type?: string | null;
    make?: string | null;
    model?: string | null;
  }>;
  contact?: {
    email?: string | null;
    phone?: string | null;
    url?: string | null;
  } | null;
};

export function facilityToForm(
  facility: LooseFacility,
  taxonomy: TaxonomyProcess[],
): FacilityFormState {
  const byId = new Map(taxonomy.map((p) => [p.canonical_id, p]));
  const processes = facility.manufacturing_processes ?? [];
  const selectedParents = new Set<string>();
  const selectedSubtypes = new Set<string>();

  for (const pid of processes) {
    const node = byId.get(pid);
    if (!node) {
      selectedParents.add(pid);
      continue;
    }
    if (node.parent) {
      selectedSubtypes.add(pid);
      selectedParents.add(node.parent);
    } else {
      selectedParents.add(pid);
    }
  }

  const addr = facility.location?.address;
  return {
    ...emptyFacilityForm(),
    name: facility.name ?? "",
    facilityStatus: asStatus(facility.facility_status),
    accessType: asAccess(facility.access_type),
    description: facility.description ?? "",
    city: addr?.city ?? facility.location?.city ?? "",
    region: addr?.region ?? facility.location?.region ?? "",
    country: addr?.country ?? facility.location?.country ?? "",
    street: addr?.street ?? "",
    selectedParents: Array.from(selectedParents),
    selectedSubtypes: Array.from(selectedSubtypes),
    openingHours: facility.opening_hours ?? "",
    contactEmail: facility.contact?.email ?? "",
    contactPhone: facility.contact?.phone ?? "",
    contactUrl: facility.contact?.url ?? "",
    equipment: (facility.equipment ?? [])
      .filter((e) => e.make || e.model)
      .map((e) => ({
        processId: e.manufacturing_process || e.equipment_type || "",
        make: e.make ?? "",
        model: e.model ?? "",
      })),
  };
}

export function importJsonToForm(
  text: string,
  taxonomy: TaxonomyProcess[],
): { form: FacilityFormState | null; error: string | null } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { form: null, error: "Invalid JSON." };
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { form: null, error: "JSON must be an object." };
  }
  return { form: facilityToForm(parsed as LooseFacility, taxonomy), error: null };
}

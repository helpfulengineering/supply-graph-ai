/**
 * Which family of making a process belongs to — the thing its swatch colours.
 *
 * Six names for 51 taxonomy ids, because a categorical scale is only readable
 * while its stops are few. They are the taxonomy's own sections
 * (`src/config/taxonomy/processes.yaml`) with two folded in: assembly sits
 * under joining, heat treatment under finishing. Both folds are of a kind —
 * bolting a bracket on and welding it are the same intent, and annealing a
 * part is the last thing done to it, like polishing it.
 *
 * `other` is the taxonomy's remainder (sewing, testing, packaging), not a
 * sixth family, and it is painted a neutral rather than a hue for that reason.
 */
export type ProcessFamily =
  | "additive"
  | "subtractive"
  | "forming"
  | "joining"
  | "finishing"
  | "other";

/**
 * Keyed by the taxonomy id, never by the humanized label — the same rule the
 * glyph table follows, so rewording "CNC machining" cannot silently drop a
 * process out of its family.
 */
const BY_ID: Record<string, ProcessFamily> = {
  "3d_printing": "additive",
  "3d_printing_fdm": "additive",
  "3d_printing_sla": "additive",
  "3d_printing_sls": "additive",
  "3d_printing_dlp": "additive",

  cnc_machining: "subtractive",
  cnc_milling: "subtractive",
  cnc_turning: "subtractive",
  precision_machining: "subtractive",
  laser_cutting: "subtractive",
  vinyl_cutting: "subtractive",
  water_jet_cutting: "subtractive",
  plasma_cutting: "subtractive",
  cutting: "subtractive",
  sawing: "subtractive",
  shearing: "subtractive",
  drilling: "subtractive",
  deburring: "subtractive",

  welding: "joining",
  tig_welding: "joining",
  mig_welding: "joining",
  arc_welding: "joining",
  brazing: "joining",
  soldering: "joining",
  assembly: "joining",
  mechanical_assembly: "joining",
  electronics_assembly: "joining",
  pcb_assembly: "joining",
  pcb_fabrication: "joining",
  electronic_circuitry: "joining",

  sheet_metal_forming: "forming",
  injection_molding: "forming",
  casting: "forming",
  forging: "forming",
  bending: "forming",

  grinding: "finishing",
  polishing: "finishing",
  sanding: "finishing",
  surface_finishing: "finishing",
  coating: "finishing",
  painting: "finishing",
  anodizing: "finishing",
  electroplating: "finishing",
  post_processing: "finishing",
  heat_treatment: "finishing",
  annealing: "finishing",
  tempering: "finishing",
  quenching: "finishing",

  sewing: "other",
  testing: "other",
  packaging: "other",
};

/**
 * Families, for ids the table does not name — a federated peer may send a
 * variant this app has never carried, and `3d_printing_mjf` is still additive.
 * Longest prefix wins, as in the glyph table.
 */
const PREFIXES: [string, ProcessFamily][] = [
  ["3d_printing", "additive"],
  ["cnc", "subtractive"],
  ["laser", "subtractive"],
  ["cutting", "subtractive"],
  ["welding", "joining"],
  ["assembly", "joining"],
  ["pcb", "joining"],
];

/**
 * `null`, not `other`, for a string that is not a process at all: `other` is a
 * claim about where something sits in the taxonomy, and an unrecognized value
 * has earned no claim. Callers draw no swatch for it.
 */
export function processFamily(process: string): ProcessFamily | null {
  const id = process.trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (BY_ID[id]) return BY_ID[id];

  let best: [string, ProcessFamily] | null = null;
  for (const entry of PREFIXES) {
    const [prefix] = entry;
    const matches = id.startsWith(`${prefix}_`) || id.endsWith(`_${prefix}`);
    if (matches && (!best || prefix.length > best[0].length)) best = entry;
  }
  return best ? best[1] : null;
}

/** The family's swatch fill. Tokens live in styles/tokens.css. */
export const PROCESS_FAMILY_SWATCH: Record<ProcessFamily, string> = {
  additive: "bg-process-additive",
  subtractive: "bg-process-subtractive",
  forming: "bg-process-forming",
  joining: "bg-process-joining",
  finishing: "bg-process-finishing",
  other: "bg-process-other",
};

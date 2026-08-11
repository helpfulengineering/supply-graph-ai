import type { JSX } from "react";
import {
  BenchGrindersIcon,
  BlowerIcon,
  BobbinIcon,
  CaliperIcon,
  CementSlinceIcon,
  CncIcon,
  CncMachineIcon,
  ControlIcon,
  CutterIcon,
  DrillingMachineIcon,
  ElectricMotorIcon,
  ElectricalPanelIcon,
  ExhaustFanIcon,
  FilamentIcon,
  GearsIcon,
  GlueGunIcon,
  GrindingMachineIcon,
  HacksawIcon,
  HammerIcon,
  LaserCutterIcon,
  LatheIcon,
  LayerThicknessIcon,
  LiquidIcon,
  MachineIcon,
  MetalCuttingMachineIcon,
  OpenAndWrenchIcon,
  PackingIcon,
  SawIcon,
  ScissorsIcon,
  SelectiveLaserMeltingIcon,
  SolderIcon,
  SolderingStationIcon,
  SprayPaintIcon,
  TestLabIcon,
  ThreeDPrinterIcon,
  VacuumCleanerIcon,
  ViseIcon,
  WeldingIcon,
  type IconProps,
} from "./index";

type Icon = (props: IconProps) => JSX.Element;

/**
 * Canonical process id to glyph — every process in the taxonomy has one.
 *
 * Keyed by the taxonomy id (`src/config/taxonomy/processes.yaml`), never by the
 * humanized label, so rewording "CNC machining" cannot silently detach an icon
 * from its process.
 *
 * Reuse is deliberate where the tool really is the same: plasma cutting and
 * sheet metal forming are both the metal-cutting machine, and the four
 * heat-treatment processes are one furnace. Inventing a distinct glyph per row
 * would mean picking pictures that do not mean anything, which is worse than an
 * honest repeat.
 */
const BY_ID: Record<string, Icon> = {
  // Additive
  "3d_printing": ThreeDPrinterIcon,
  "3d_printing_fdm": FilamentIcon,
  "3d_printing_sla": LiquidIcon,
  "3d_printing_sls": SelectiveLaserMeltingIcon,
  "3d_printing_dlp": LayerThicknessIcon,

  // Subtractive
  cnc_machining: CncMachineIcon,
  cnc_milling: CncIcon,
  cnc_turning: LatheIcon,
  precision_machining: CaliperIcon,
  laser_cutting: LaserCutterIcon,
  vinyl_cutting: CutterIcon,
  water_jet_cutting: BlowerIcon,
  plasma_cutting: MetalCuttingMachineIcon,
  cutting: CutterIcon,
  sawing: SawIcon,
  shearing: ScissorsIcon,
  drilling: DrillingMachineIcon,
  deburring: HacksawIcon,

  // Joining
  welding: WeldingIcon,
  tig_welding: WeldingIcon,
  mig_welding: WeldingIcon,
  arc_welding: WeldingIcon,
  brazing: GlueGunIcon,
  soldering: SolderingStationIcon,

  // Forming
  sheet_metal_forming: MetalCuttingMachineIcon,
  injection_molding: MachineIcon,
  casting: CementSlinceIcon,
  forging: HammerIcon,
  bending: ViseIcon,

  // Assembly
  assembly: GearsIcon,
  mechanical_assembly: OpenAndWrenchIcon,
  electronics_assembly: ElectricalPanelIcon,
  pcb_assembly: SolderIcon,
  pcb_fabrication: ElectricalPanelIcon,
  electronic_circuitry: ControlIcon,

  // Finishing
  grinding: GrindingMachineIcon,
  polishing: BenchGrindersIcon,
  sanding: BenchGrindersIcon,
  surface_finishing: BenchGrindersIcon,
  coating: SprayPaintIcon,
  painting: SprayPaintIcon,
  anodizing: LiquidIcon,
  electroplating: ElectricMotorIcon,
  post_processing: VacuumCleanerIcon,

  // Heat
  heat_treatment: ExhaustFanIcon,
  annealing: ExhaustFanIcon,
  tempering: ExhaustFanIcon,
  quenching: ExhaustFanIcon,

  // Other
  sewing: BobbinIcon,
  testing: TestLabIcon,
  packaging: PackingIcon,
};

/**
 * Families, for ids the table does not name.
 *
 * The taxonomy nests variants under a parent, and a peer may send one this app
 * has never seen — `3d_printing_mjf` should still draw a printer rather than
 * nothing. Longest prefix wins, so `3d_printing_sla` keeps its own glyph.
 */
const FAMILIES: [string, Icon][] = [
  ["3d_printing", ThreeDPrinterIcon],
  ["cnc", CncMachineIcon],
  ["welding", WeldingIcon],
  ["laser", LaserCutterIcon],
  ["assembly", GearsIcon],
  ["pcb", ElectricalPanelIcon],
];

export function processIcon(processId: string): Icon | null {
  const id = processId.trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (BY_ID[id]) return BY_ID[id];

  let best: [string, Icon] | null = null;
  for (const entry of FAMILIES) {
    const [prefix] = entry;
    const matches = id.startsWith(`${prefix}_`) || id.endsWith(`_${prefix}`);
    if (matches && (!best || prefix.length > best[0].length)) best = entry;
  }
  return best ? best[1] : null;
}

/** The taxonomy ids this module draws, for the coverage test and the gallery. */
export const MAPPED_PROCESS_IDS = Object.keys(BY_ID);

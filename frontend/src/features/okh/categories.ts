import type { OkhManifest } from "../../types/okh";

/**
 * Provisional device categorization (pure, unit-tested).
 *
 * A lightweight keyword→category dictionary applied to a manifest's `function`
 * (rich in the corpus), `title`, and `keywords`. Categories are **multi-valued**
 * — a device may fall under several — and this is deliberately a placeholder for
 * the real, service-backed Device Category Taxonomy (Epic #199): once that lands
 * the category facet swaps from derived to service-backed with no UX change.
 * Keep the rules broad and honest, not tuned to any one corpus.
 */

export const UNCATEGORIZED = "Uncategorized";

interface CategoryRule {
  category: string;
  keywords: string[];
}

const CATEGORY_RULES: CategoryRule[] = [
  {
    category: "Laboratory & Bio",
    keywords: ["centrifuge", "incubator", "spectrophotometer", "photobioreactor", "thermocycler", "pcr", "gel", "dna", "assay", "bioreactor", "laboratory", "lab", "stirrer", "reagent"],
  },
  {
    category: "Optics & Imaging",
    keywords: ["microscope", "camera", "webcam", "optical", "optics", "lens", "imaging", "spectro", "photo"],
  },
  {
    category: "Fluid Handling",
    keywords: ["pump", "syringe", "peristaltic", "fluid", "liquid", "dispense", "valve", "flow"],
  },
  {
    category: "Thermal Control",
    keywords: ["thermal", "temperature", "incubator", "thermocycler", "heat", "cooling", "furnace"],
  },
  {
    category: "Computing & Electronics",
    keywords: ["computer", "single-board", "board", "arm", "cpu", "processor", "beaglebone", "raspberry", "microcontroller", "pcb", "electronics", "sensor"],
  },
  {
    category: "Medical & PPE",
    keywords: ["ventilator", "respirator", "mask", "shield", "ppe", "medical", "surgical", "prosthetic"],
  },
  {
    category: "Test & Measurement",
    keywords: ["test", "calibration", "measurement", "meter", "gauge", "analyzer"],
  },
];

/** Categories a manifest belongs to (multi-valued); [UNCATEGORIZED] if none. */
export function deriveCategories(item: OkhManifest): string[] {
  const haystack = [item.function, item.title, ...(item.keywords ?? [])]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  const matched = CATEGORY_RULES.filter((rule) =>
    rule.keywords.some((kw) => haystack.includes(kw)),
  ).map((r) => r.category);

  return matched.length > 0 ? matched : [UNCATEGORIZED];
}

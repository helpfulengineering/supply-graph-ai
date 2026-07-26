/**
 * Guided review model (pure, unit-tested) — Slice B.
 *
 * OKH has 6 required fields and ~47 optional ones. Presenting 53 inputs after a
 * heuristic extraction is not review, it is a wall. So fields are tiered by what
 * a human actually has to decide:
 *
 *   Tier 1 — required. Save is gated on these being present.
 *   Tier 2 — the ones that change outcomes: what drives matching, and what makes
 *            a design findable. Not required, but the reason to bother.
 *   Tier 3 — the long tail. Collapsed by default.
 *
 * Only scalars and simple lists get structured editors. Nested structures
 * (materials, BOM) are shown read-only with a raw-JSON escape hatch, because a
 * half-built nested editor that silently drops fields is worse than an honest
 * text area. Those are also the most error-prone generation outputs, which is
 * why a proper nested editor is the top follow-up.
 */

export type FieldKind = "scalar" | "list" | "nested";

export interface FieldSpec {
  /** Dot path into the manifest, e.g. "license.hardware". */
  path: string;
  label: string;
  kind: FieldKind;
  hint?: string;
}

export interface TierGroup {
  id: string;
  title: string;
  blurb?: string;
  fields: FieldSpec[];
}

/**
 * Required by OKH. `license` and `licensor` are objects, so their leaves are
 * exposed individually — a required field the user cannot fix without dropping
 * to raw JSON would defeat the point of a guided review.
 */
export const TIER1: FieldSpec[] = [
  { path: "title", label: "Title", kind: "scalar" },
  { path: "version", label: "Version", kind: "scalar" },
  {
    path: "function",
    label: "Function",
    kind: "scalar",
    hint: "What the thing does, in one or two sentences.",
  },
  { path: "documentation_language", label: "Documentation language", kind: "scalar" },
  { path: "licensor.name", label: "Licensor name", kind: "scalar" },
  { path: "license.hardware", label: "Hardware licence", kind: "scalar" },
];

/** Paths whose presence satisfies the required-field gate. */
export const REQUIRED_PATHS: string[] = TIER1.map((f) => f.path);

export const TIER2_GROUPS: TierGroup[] = [
  {
    id: "matching",
    title: "What drives matching",
    blurb:
      "These decide which workshops can build this. Getting them right matters more than anything else on this page.",
    fields: [
      {
        path: "manufacturing_processes",
        label: "Manufacturing processes",
        kind: "list",
        hint: "The processes needed to produce this design.",
      },
      { path: "tsdc", label: "Technology-specific documentation criteria", kind: "list" },
      {
        path: "materials",
        label: "Materials",
        kind: "nested",
        hint: "Extracted materials are frequently noisy — check them.",
      },
      { path: "bom", label: "Bill of materials", kind: "nested" },
    ],
  },
  {
    id: "discoverability",
    title: "Being found",
    blurb: "How someone searching comes across this design.",
    fields: [
      { path: "description", label: "Description", kind: "scalar" },
      { path: "repo", label: "Repository", kind: "scalar" },
      { path: "keywords", label: "Keywords", kind: "list" },
      { path: "documentation_home", label: "Documentation home", kind: "scalar" },
    ],
  },
];

const CLASSIFIED = new Set<string>([
  ...TIER1.map((f) => f.path),
  ...TIER2_GROUPS.flatMap((g) => g.fields.map((f) => f.path)),
  // Roots covered by a tier-1 leaf; don't also show the whole object in tier 3.
  "license",
  "licensor",
]);

/** Read a dot path out of a manifest. */
export function getPath(manifest: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && !Array.isArray(acc)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, manifest);
}

/** Immutably set a dot path, creating intermediate objects as needed. */
export function setPath(
  manifest: Record<string, unknown>,
  path: string,
  value: unknown,
): Record<string, unknown> {
  const [head, ...rest] = path.split(".");
  const next = { ...manifest };
  if (rest.length === 0) {
    next[head] = value;
    return next;
  }
  const child = next[head];
  const childObj =
    child && typeof child === "object" && !Array.isArray(child)
      ? (child as Record<string, unknown>)
      : {};
  next[head] = setPath(childObj, rest.join("."), value);
  return next;
}

export function isEmptyValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim() === "";
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value as object).length === 0;
  return false;
}

/** Required paths that are still empty. Save is blocked while this is non-empty. */
export function missingRequired(manifest: Record<string, unknown>): string[] {
  return REQUIRED_PATHS.filter((p) => isEmptyValue(getPath(manifest, p)));
}

/**
 * Everything present in the manifest that no tier claims — shown collapsed, so
 * a generated field is never silently hidden from the person reviewing it.
 */
export function tier3Fields(manifest: Record<string, unknown>): FieldSpec[] {
  return Object.keys(manifest)
    .filter((key) => !CLASSIFIED.has(key))
    .sort()
    .map((key) => {
      const value = manifest[key];
      const kind: FieldKind = Array.isArray(value)
        ? value.every((v) => typeof v !== "object" || v === null)
          ? "list"
          : "nested"
        : value !== null && typeof value === "object"
          ? "nested"
          : "scalar";
      return { path: key, label: humanizeKey(key), kind };
    });
}

export function humanizeKey(key: string): string {
  const text = key.replace(/[_.]/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

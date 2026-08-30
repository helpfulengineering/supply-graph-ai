import { z } from "zod";

/**
 * The record of how a generated manifest was produced.
 *
 * Distinct from `/api/okh/{id}/provenance`, which is *record* provenance —
 * who published a manifest and when. This is generation provenance: which
 * layer produced each field, by what method, and from where.
 *
 * It arrives as `Dict[str, Any]` server-side, so codegen types it
 * `Record<string, unknown>` and the compiler can vouch for nothing. Parsed at
 * the boundary for the reason in docs/architecture/api-response-contracts.md:
 * a drift then names the field instead of throwing somewhere inside a render.
 */

/** `looseObject` throughout: a parse that strips server fields is a parse that loses data. */
const stageSchema = z.looseObject({
  seq: z.number(),
  stage: z.string(),
  fraction: z.number(),
  message: z.string().nullish(),
  ts: z.string().nullish(),
});

const fieldSchema = z.looseObject({
  layer: z.string(),
  method: z.string(),
  confidence: z.number(),
  source: z.string(),
});

export const generationProvenanceSchema = z.looseObject({
  schema: z.string(),
  generated_at: z.string().nullish(),
  source_url: z.string().nullish(),
  stages: z.array(stageSchema),
  fields: z.record(z.string(), fieldSchema),
});

export type ProvenanceStage = z.infer<typeof stageSchema>;
export type ProvenanceField = z.infer<typeof fieldSchema>;
export type GenerationProvenance = z.infer<typeof generationProvenanceSchema>;

/** One field, with its name, for rendering as a row. */
export interface NamedField extends ProvenanceField {
  name: string;
}

/**
 * Parse a record from a run or a file.
 *
 * Returns `null` rather than throwing: a record is supporting detail, and a
 * malformed one should cost the panel, not the page that ran the generation.
 */
export function readGenerationProvenance(
  value: unknown,
): GenerationProvenance | null {
  const parsed = generationProvenanceSchema.safeParse(value);
  return parsed.success ? parsed.data : null;
}

export interface ReviewGroup {
  id: string;
  /** What the reader is being told about this set. */
  title: string;
  /** Why it is grouped this way, in the reader's terms. */
  note: string;
  /** How much scrutiny this group asks for. */
  weight: "none" | "check" | "settled";
  fields: NamedField[];
}

/** Layers where a model or a rule decided, rather than copied. */
const INFERRED = new Set(["heuristic", "nlp", "llm"]);
/** Layers that read or restructured what was already there. */
const TAKEN = new Set(["direct", "bom_normalization"]);

/**
 * Group the fields by how much checking each deserves.
 *
 * The ordering is the point: a reviewer's time goes to what a model guessed,
 * not to a title copied out of repository metadata. Empty groups are dropped,
 * so a clean run does not render three headings over nothing.
 *
 * Every field lands in exactly one group, including one whose layer this does
 * not recognise — an unknown layer is a reason to show a field prominently,
 * never a reason to drop it from the page.
 */
export function groupForReview(record: GenerationProvenance): ReviewGroup[] {
  const named: NamedField[] = Object.entries(record.fields)
    .map(([name, field]) => ({ name, ...field }))
    .sort((a, b) => a.name.localeCompare(b.name));

  const notFound = named.filter((f) => f.confidence <= 0);
  const rest = named.filter((f) => f.confidence > 0);
  const inferred = rest.filter((f) => INFERRED.has(f.layer));
  const taken = rest.filter((f) => TAKEN.has(f.layer));
  const edited = rest.filter((f) => f.layer === "user_edit");
  const unrecognised = rest.filter(
    (f) => !INFERRED.has(f.layer) && !TAKEN.has(f.layer) && f.layer !== "user_edit",
  );

  return [
    {
      id: "not-found",
      title: "Nothing was found",
      note: "the generator looked and came back empty",
      weight: "none" as const,
      fields: notFound,
    },
    {
      id: "inferred",
      title: "Inferred from prose",
      note: "a model or a heuristic read text and decided; worth confirming",
      weight: "check" as const,
      fields: inferred,
    },
    {
      id: "unrecognised",
      title: "Produced by an unfamiliar layer",
      note: "this view does not know this layer; treat it as unchecked",
      weight: "check" as const,
      fields: unrecognised,
    },
    {
      id: "edited",
      title: "Edited by hand",
      note: "a person set this during review",
      weight: "settled" as const,
      fields: edited,
    },
    {
      id: "taken",
      title: "Read straight from the repository",
      note: "copied from metadata or a file; little to check",
      weight: "settled" as const,
      fields: taken,
    },
  ].filter((group) => group.fields.length > 0);
}

/**
 * The run so far, in the shape a finished record has.
 *
 * Fields stay empty until the run ends — they are only known once the manifest
 * exists — so this is honestly partial rather than a different kind of thing.
 * Building it here means the live view and the downloaded record are the same
 * structure rendered by the same component, which is the whole reason the
 * record was designed before the live view.
 */
export function liveRecordFrom(
  stages: ProvenanceStage[],
  sourceUrl: string | null,
): GenerationProvenance {
  return {
    schema: "ohm-generation-provenance/v1",
    generated_at: null,
    source_url: sourceUrl,
    stages,
    fields: {},
  };
}

/** Seconds each stage ran, from the gap to the next one. The last has no successor. */
export function stageDurations(
  stages: ProvenanceStage[],
): Array<ProvenanceStage & { seconds: number | null }> {
  return stages.map((stage, i) => {
    const next = stages[i + 1];
    const from = stage.ts ? Date.parse(stage.ts) : NaN;
    const to = next?.ts ? Date.parse(next.ts) : NaN;
    const seconds =
      Number.isFinite(from) && Number.isFinite(to) ? (to - from) / 1000 : null;
    return { ...stage, seconds };
  });
}

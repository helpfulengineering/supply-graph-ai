import { describe, expect, it } from "vitest";
import {
  groupForReview,
  readGenerationProvenance,
  stageDurations,
  type GenerationProvenance,
} from "./generationProvenance";

const record: GenerationProvenance = {
  schema: "ohm-generation-provenance/v1",
  generated_at: "2026-08-29T12:00:00+00:00",
  source_url: "https://github.com/org/repo",
  stages: [
    { seq: 0, stage: "clone", fraction: 0.12, message: "Cloning", ts: "2026-08-29T12:00:00Z" },
    { seq: 1, stage: "nlp", fraction: 0.4, message: null, ts: "2026-08-29T12:00:04Z" },
    { seq: 2, stage: "quality", fraction: 1, message: null, ts: "2026-08-29T12:00:06Z" },
  ],
  fields: {
    title: { layer: "direct", method: "metadata_name", confidence: 0.98, source: "metadata.name" },
    description: { layer: "nlp", method: "readme_summary", confidence: 0.62, source: "README.md" },
    version: { layer: "direct", method: "none", confidence: 0, source: "no_version_found" },
    notes: { layer: "user_edit", method: "review", confidence: 1, source: "user_input" },
  },
};

describe("readGenerationProvenance", () => {
  it("accepts a well-formed record", () => {
    expect(readGenerationProvenance(record)?.schema).toBe(
      "ohm-generation-provenance/v1",
    );
  });

  it("keeps fields the schema does not describe", () => {
    // A stripping parse would silently lose server data — the same hazard that
    // makes response_model dangerous to hand-write, rebuilt at the client.
    const withExtra = { ...record, future_key: "kept" };
    expect(readGenerationProvenance(withExtra)).toMatchObject({
      future_key: "kept",
    });
  });

  it("returns null for a malformed record rather than throwing", () => {
    // The record is supporting detail: a bad one costs the panel, not the page.
    expect(readGenerationProvenance({ schema: "x" })).toBeNull();
    expect(readGenerationProvenance(null)).toBeNull();
    expect(readGenerationProvenance({ ...record, fields: "nope" })).toBeNull();
  });
});

describe("groupForReview", () => {
  it("puts what needs checking before what does not", () => {
    const ids = groupForReview(record).map((g) => g.id);
    expect(ids.indexOf("not-found")).toBeLessThan(ids.indexOf("inferred"));
    expect(ids.indexOf("inferred")).toBeLessThan(ids.indexOf("taken"));
  });

  it("treats a zero-confidence field as not found, whatever its layer", () => {
    const notFound = groupForReview(record).find((g) => g.id === "not-found");
    expect(notFound?.fields.map((f) => f.name)).toEqual(["version"]);
  });

  it("separates a hand edit from a metadata read", () => {
    const groups = Object.fromEntries(
      groupForReview(record).map((g) => [g.id, g.fields.map((f) => f.name)]),
    );
    expect(groups.edited).toEqual(["notes"]);
    expect(groups.taken).toEqual(["title"]);
  });

  it("shows a field from an unknown layer rather than dropping it", () => {
    const withUnknown: GenerationProvenance = {
      ...record,
      fields: {
        ...record.fields,
        mystery: { layer: "quantum", method: "?", confidence: 0.5, source: "?" },
      },
    };
    const unrecognised = groupForReview(withUnknown).find(
      (g) => g.id === "unrecognised",
    );
    expect(unrecognised?.fields.map((f) => f.name)).toEqual(["mystery"]);
  });

  it("accounts for every field exactly once", () => {
    // The invariant that matters: this view must not be able to lose a field.
    const seen = groupForReview(record).flatMap((g) => g.fields.map((f) => f.name));
    expect(seen.sort()).toEqual(Object.keys(record.fields).sort());
  });

  it("drops empty groups so a clean run shows no empty headings", () => {
    const clean: GenerationProvenance = {
      ...record,
      fields: { title: record.fields.title },
    };
    expect(groupForReview(clean).map((g) => g.id)).toEqual(["taken"]);
  });
});

describe("stageDurations", () => {
  it("measures each stage by the gap to the next", () => {
    const [clone, nlp, quality] = stageDurations(record.stages);
    expect(clone.seconds).toBe(4);
    expect(nlp.seconds).toBe(2);
    // Nothing follows the last stage, so its length is unknowable from the log.
    expect(quality.seconds).toBeNull();
  });

  it("reports null rather than guessing when a timestamp is missing", () => {
    const [only] = stageDurations([
      { seq: 0, stage: "clone", fraction: 0.1, message: null, ts: null },
    ]);
    expect(only.seconds).toBeNull();
  });
});

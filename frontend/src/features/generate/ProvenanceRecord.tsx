"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { PANEL, PANEL_MUTED } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION } from "@/components/ui/typography";
import { cn } from "@/lib/utils";
import {
  groupForReview,
  stageDurations,
  type GenerationProvenance,
  type NamedField,
  type ReviewGroup,
} from "./generationProvenance";

/**
 * How a generated manifest was produced.
 *
 * Three readings of one record, because a reviewer arrives with one of three
 * questions and no single ordering answers all of them:
 *
 *   Review — what needs checking?
 *   Fields — is this particular value right?
 *   Stages — what did the run do?
 *
 * Nothing is duplicated between them; they differ in what they put first.
 *
 * Rendered from a record handed in, never fetched here: generation is not
 * persisted server-side, so the same view serves a run that just finished and
 * a sidecar someone kept on disk (#393 supplies the second).
 */
type View = "review" | "fields" | "stages";

const VIEWS = [
  { value: "review" as const, label: "Review" },
  { value: "fields" as const, label: "Fields" },
  { value: "stages" as const, label: "Stages" },
];

/** Layer names are the API's own; a badge tints the ones that inferred. */
function LayerBadge({ layer }: { layer: string }) {
  const variant =
    layer === "llm" || layer === "nlp" || layer === "heuristic"
      ? "yellow"
      : "default";
  return (
    <Badge variant={variant}>
      <span className="font-mono">{layer}</span>
    </Badge>
  );
}

function Confidence({ value }: { value: number }) {
  if (value <= 0) {
    return (
      <span className="font-mono text-caption text-destructive-ink">
        not found
      </span>
    );
  }
  return (
    <span className="font-mono text-caption tabular-nums">
      {value.toFixed(2)}
    </span>
  );
}

/** One field as a row: what it is, where it came from, how sure the run was. */
function FieldRow({ field }: { field: NamedField }) {
  return (
    <li className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-2.5">
      <span className="text-small text-foreground">{field.name}</span>
      <span className={cn(CAPTION, "font-mono")}>{field.source}</span>
      <span className="ml-auto flex items-baseline gap-3">
        <LayerBadge layer={field.layer} />
        <Confidence value={field.confidence} />
      </span>
    </li>
  );
}

/** Said by whichever view has nothing, rather than leaving a blank tab. */
function NothingRecorded({ what }: { what: string }) {
  return <p className={cn(PANEL_MUTED, BODY_MUTED)}>This run recorded no {what}.</p>;
}

function ReviewList({ groups }: { groups: ReviewGroup[] }) {
  if (groups.length === 0) return <NothingRecorded what="fields" />;
  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <section
          key={group.id}
          aria-labelledby={`provenance-${group.id}`}
          className={PANEL}
        >
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <SectionHeading id={`provenance-${group.id}`} role="card">
              {group.title} — {group.fields.length}{" "}
              {group.fields.length === 1 ? "field" : "fields"}
            </SectionHeading>
            <p className={CAPTION}>{group.note}</p>
          </div>
          <ul className="mt-1 divide-y divide-border">
            {group.fields.map((field) => (
              <FieldRow key={field.name} field={field} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function FieldsList({ record }: { record: GenerationProvenance }) {
  const fields = Object.entries(record.fields)
    .map(([name, field]) => ({ name, ...field }))
    .sort((a, b) => a.name.localeCompare(b.name));

  if (fields.length === 0) return <NothingRecorded what="fields" />;
  return (
    <section aria-labelledby="provenance-fields" className={PANEL}>
      <SectionHeading id="provenance-fields" role="card">
        Every field — {fields.length}
      </SectionHeading>
      <ul className="mt-1 divide-y divide-border">
        {fields.map((field) => (
          <li key={field.name} className="px-4 py-2.5">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="text-small text-foreground">{field.name}</span>
              <span className="ml-auto flex items-baseline gap-3">
                <LayerBadge layer={field.layer} />
                <Confidence value={field.confidence} />
              </span>
            </div>
            <dl className="mt-1 flex flex-wrap gap-x-6 gap-y-0.5">
              <div className="flex items-baseline gap-1.5">
                <dt className={CAPTION}>method</dt>
                <dd className={cn(CAPTION, "font-mono text-foreground")}>
                  {field.method}
                </dd>
              </div>
              <div className="flex items-baseline gap-1.5">
                <dt className={CAPTION}>read from</dt>
                <dd className={cn(CAPTION, "font-mono text-foreground")}>
                  {field.source}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </section>
  );
}

function StageList({
  record,
  live,
}: {
  record: GenerationProvenance;
  live: boolean;
}) {
  const stages = stageDurations(record.stages);
  if (stages.length === 0) return <NothingRecorded what="stages" />;
  return (
    <section aria-labelledby="provenance-stages" className={PANEL}>
      <SectionHeading id="provenance-stages" role="card">
        What ran — {stages.length} {stages.length === 1 ? "stage" : "stages"}
      </SectionHeading>
      <ol className="mt-1 divide-y divide-border">
        {stages.map((stage, i) => (
          <li
            key={stage.seq}
            className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-2.5"
          >
            <span className="font-mono text-small text-foreground">
              {stage.stage}
            </span>
            {/* A stage is emitted when it BEGINS, so while a run is going the
                last row is the one in flight rather than one that finished. */}
            {live && i === stages.length - 1 ? (
              <span className={CAPTION}>running</span>
            ) : null}
            {stage.message ? (
              <span className={CAPTION}>{stage.message}</span>
            ) : null}
            <span className="ml-auto flex items-baseline gap-3">
              {stage.seconds === null ? null : (
                <span className={cn(CAPTION, "font-mono tabular-nums")}>
                  {stage.seconds.toFixed(1)}s
                </span>
              )}
              <span className={cn(CAPTION, "font-mono tabular-nums")}>
                {Math.round(stage.fraction * 100)}%
              </span>
            </span>
          </li>
        ))}
      </ol>
      <p className={cn(CAPTION, "mt-2 px-4")}>
        Every stage the run reported, in order — including ones that finished
        faster than a poll, which the progress bar alone cannot show.
      </p>
    </section>
  );
}

export function ProvenanceRecord({
  record,
  live = false,
}: {
  record: GenerationProvenance;
  /**
   * The run is still going: the record grows under the reader.
   *
   * Opens on Stages, because that is the view with anything in it — fields
   * arrive only when the run finishes, so Review would greet a watching reader
   * with "no fields". The chosen view is then theirs: this seeds the initial
   * state and never yanks them elsewhere when the run ends.
   */
  live?: boolean;
}) {
  const [view, setView] = useState<View>(live ? "stages" : "review");
  const groups = groupForReview(record);

  return (
    <section aria-labelledby="provenance-record" className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <SectionHeading id="provenance-record" role="title">
          {live
            ? "How this design is being generated"
            : "How this design was generated"}
        </SectionHeading>
        {record.source_url ? (
          <span className={cn(CAPTION, "font-mono")}>{record.source_url}</span>
        ) : null}
      </div>

      <SegmentedControl
        label="How to read the generation record"
        value={view}
        options={VIEWS}
        onChange={setView}
      />

      {view === "review" ? <ReviewList groups={groups} /> : null}
      {view === "fields" ? <FieldsList record={record} /> : null}
      {view === "stages" ? <StageList record={record} live={live} /> : null}
    </section>
  );
}

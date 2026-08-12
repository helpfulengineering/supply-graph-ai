"use client";

import type { ChecklistItem } from "@/api/ohm/asset";
import { Badge } from "@/components/ui/Badge";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { FIELD_SM } from "@/components/ui/field";
import { CAPTION } from "@/components/ui/typography";
import { cn } from "@/lib/utils";
import {
  COMPONENT_CONDITIONS,
  conditionImpliesWork,
} from "./componentCondition";
import type { ComponentCondition } from "./componentCondition";
import type { TriageRowState, TriState } from "./triageFormModel";

/** "yes / no / not stated" — a tri-state a checkbox cannot express. */
const TRI_OPTIONS = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "unset", label: "Not stated" },
] as const;

type TriKey = (typeof TRI_OPTIONS)[number]["value"];

const toKey = (value: TriState): TriKey =>
  value === true ? "yes" : value === false ? "no" : "unset";
const fromKey = (key: TriKey): TriState =>
  key === "yes" ? true : key === "no" ? false : null;

function TriControl({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: TriState;
  onChange: (next: TriState) => void;
}) {
  return (
    <div className="min-w-0">
      <SegmentedControl<TriKey>
        label={label}
        value={toKey(value)}
        options={TRI_OPTIONS}
        onChange={(key) => onChange(fromKey(key))}
      />
      <p className={cn(CAPTION, "mt-1")}>{hint}</p>
    </div>
  );
}

/**
 * One component in a triage session.
 *
 * The manifest's own flags are shown as quiet badges, visually distinct from
 * what the technician is entering — a row that mixed "the design says this is
 * salvageable" with "I observed it damaged" would read as one claim.
 *
 * The three follow-up flags appear only when the condition implies work. On an
 * intact component they stay hidden and serialise as null, which is what the
 * server wants: null lets it infer the flag from condition plus design, where
 * a stated false is the technician overruling that. Showing three tri-state
 * controls per row for the common case would be the wrong price.
 */
export function TriageComponentRow({
  item,
  row,
  onChange,
  onCondition,
}: {
  item: ChecklistItem;
  row: TriageRowState;
  onChange: (patch: Partial<TriageRowState>) => void;
  onCondition: (condition: ComponentCondition) => void;
}) {
  const showFlags = conditionImpliesWork(row.condition);
  const notesId = `triage-notes-${item.component_name}`;

  return (
    <div className="border-b border-border py-4 last:border-0">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-foreground">
          {item.component_name}
        </span>
        {item.part_number && (
          <span className={cn(CAPTION, "font-mono")}>{item.part_number}</span>
        )}
        {item.replaceable && <Badge>replaceable</Badge>}
        {item.salvageable && <Badge>salvageable</Badge>}
        {item.consumable && <Badge>consumable</Badge>}
        {item.assessed && (
          <span className={cn(CAPTION, "ml-auto")}>previously assessed</span>
        )}
      </div>

      <div className="mt-3">
        <SegmentedControl<ComponentCondition>
          label={`Condition of ${item.component_name}`}
          value={row.condition ?? ("" as ComponentCondition)}
          options={COMPONENT_CONDITIONS.map((c) => ({
            value: c.value,
            label: c.label,
          }))}
          onChange={onCondition}
        />
      </div>

      {showFlags && (
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <TriControl
            label={`Repair feasible for ${item.component_name}`}
            hint="Repair feasible without a part?"
            value={row.repairFeasible}
            onChange={(repairFeasible) => onChange({ repairFeasible })}
          />
          <TriControl
            label={`Harvest viable for ${item.component_name}`}
            hint="Worth taking for another unit?"
            value={row.harvestViable}
            onChange={(harvestViable) => onChange({ harvestViable })}
          />
          <TriControl
            label={`Source required for ${item.component_name}`}
            hint="Needs a replacement part?"
            value={row.sourceRequired}
            onChange={(sourceRequired) => onChange({ sourceRequired })}
          />
        </div>
      )}

      <div className="mt-3">
        <label className="sr-only" htmlFor={notesId}>
          Notes on {item.component_name}
        </label>
        <input
          id={notesId}
          value={row.notes}
          onChange={(e) => onChange({ notes: e.target.value })}
          placeholder="Notes (optional)"
          className={`${FIELD_SM} w-full text-foreground focus:outline-none focus:ring-2 focus:ring-ring`}
        />
      </div>
    </div>
  );
}

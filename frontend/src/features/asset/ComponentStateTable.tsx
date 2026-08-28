"use client";

import type { ComponentState } from "@/api/ohm/asset";
import { Badge } from "@/components/ui/Badge";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { PANEL, PANEL_BODY } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION } from "@/components/ui/typography";
import { cn } from "@/lib/utils";
import { claimState } from "./claimState";
import { conditionInfo } from "./componentCondition";

/** What has actually been observed on this unit, as recorded. */
export function ComponentStateTable({
  states,
  now,
}: {
  states: readonly ComponentState[];
  now: number;
}) {
  return (
    <section aria-labelledby="components" className={cn(PANEL, PANEL_BODY)}>
      <SectionHeading id="components" role="card">
        Components
      </SectionHeading>

      {states.length === 0 ? (
        <p className={cn(BODY_MUTED, "mt-3")}>
          Nothing recorded yet. Run triage to assess this unit component by
          component.
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {states.map((state) => {
            const condition = conditionInfo(state.condition);
            const claim = claimState(state, now);
            return (
              <li
                key={state.component_name}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border pb-2 text-sm last:border-0 last:pb-0"
              >
                <span className="font-medium text-foreground">
                  {state.component_name}
                </span>
                <Badge variant={condition.tone}>{condition.label}</Badge>
                {state.notes && (
                  <span className="min-w-0 flex-1 text-muted-foreground">
                    {state.notes}
                  </span>
                )}
                {claim.claimed && (
                  <span className={CAPTION}>{claim.label}</span>
                )}
                {state.assessed_by && (
                  <span className={cn(CAPTION, "ml-auto")}>
                    by {state.assessed_by}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

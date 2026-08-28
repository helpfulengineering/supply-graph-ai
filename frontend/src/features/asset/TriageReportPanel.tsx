"use client";

import { useMemo } from "react";
import type { TriageReport } from "@/api/ohm/asset";
import { Badge } from "@/components/ui/Badge";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { PANEL, PANEL_BODY, PANEL_INSET } from "@/components/ui/surface";
import { BODY_MUTED, CAPTION, STAT_VALUE } from "@/components/ui/typography";
import { cn } from "@/lib/utils";
import { TRIAGE_ACTIONS, triageActionInfo } from "./triageAction";

/**
 * What triage concluded, grouped by what to do about it.
 *
 * The vocabulary is taught where it is used: each group carries the sentence
 * explaining how the server reached that recommendation, because "harvest" and
 * "source new" are the product's words, not English's, and a reader meeting
 * them for the first time is meeting them here.
 */
export function TriageReportPanel({ report }: { report: TriageReport }) {
  const groups = useMemo(() => {
    const byAction = new Map<string, typeof report.items>();
    for (const item of report.items ?? []) {
      const bucket = byAction.get(item.recommended_action);
      if (bucket) bucket.push(item);
      else byAction.set(item.recommended_action, [item]);
    }
    return [...byAction]
      .map(([action, items]) => ({ info: triageActionInfo(action), items }))
      .sort((a, b) => a.info.order - b.info.order);
  }, [report]);

  const summary = report.summary;

  return (
    <section aria-labelledby="triage-report" className={cn(PANEL, PANEL_BODY)}>
      <SectionHeading id="triage-report" role="card">
        Triage report
      </SectionHeading>

      {summary ? (
        <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {TRIAGE_ACTIONS.map((action) => (
            <div key={action.value} className={PANEL_INSET}>
              <dt className={CAPTION}>{action.label}</dt>
              <dd className={cn(STAT_VALUE, "mt-1")}>
                {summary[action.summaryKey] ?? 0}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      {groups.length === 0 ? (
        <p className={cn(BODY_MUTED, "mt-3")}>
          No components have been assessed yet.
        </p>
      ) : (
        <div className="mt-5 space-y-5">
          {groups.map(({ info, items }) => (
            <div key={info.value}>
              <div className="flex flex-wrap items-baseline gap-2">
                <Badge variant={info.tone}>{info.label}</Badge>
                <span className={CAPTION}>{info.meaning}</span>
              </div>
              <ul className="mt-2 space-y-1">
                {items.map((item) => (
                  <li
                    key={item.component_name}
                    className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm"
                  >
                    <span className="font-medium text-foreground">
                      {item.component_name}
                    </span>
                    {item.part_number && (
                      <span className={cn(CAPTION, "font-mono")}>
                        {item.part_number}
                      </span>
                    )}
                    {item.notes && (
                      <span className="min-w-0 flex-1 truncate text-muted-foreground">
                        {item.notes}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

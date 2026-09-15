"use client";

import { Badge } from "../../components/ui/Badge";
import { CHECKBOX } from "../../components/ui/field";
import { PANEL, PANEL_ACCENT } from "../../components/ui/surface";
import { CARD_TITLE } from "../../components/ui/typography";
import { cn } from "@/lib/utils";
import type { RankedSolution } from "./matchViewModel";
import { confidencePct, confidenceToken } from "./confidence";
import { coverageLabel } from "./nearMiss";

export function MatchResultCard({
  solution,
  selected,
  onToggle,
  selectionKey,
}: {
  solution: RankedSolution;
  selected: boolean;
  onToggle: () => void;
  selectionKey: string;
  /** Persisted solution id — the only id the visualization endpoint accepts. */
}) {
  const token = confidenceToken(solution.confidence);
  const firstLine = solution.explanation?.split("\n")[0]?.trim() ?? null;

  return (
    <div className={selected ? PANEL_ACCENT : PANEL}>
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          className={cn(CHECKBOX, "mt-1")}
          checked={selected}
          onChange={onToggle}
          aria-label={`Select ${solution.facilityName}`}
          data-selection-key={selectionKey}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  #{solution.rank}
                </span>
                <h3 className={cn(CARD_TITLE, "min-w-0 break-words")}>
                  {solution.facilityName}
                </h3>
              </div>
              {firstLine && (
                <p className="mt-1 text-sm text-muted-foreground">
                  {firstLine}
                </p>
              )}
            </div>
            {/*
              Coverage leads, confidence follows. A bare percentage was the bug:
              a facility missing a requirement read as "Medium · 67%", which
              invites "probably fine". What a person can act on is WHICH
              requirement is unmet, so say that first and keep the score as a
              secondary signal.
            */}
            <div className="flex shrink-0 flex-col items-end gap-1">
              <Badge
                variant={solution.coverage?.missing ? "yellow" : token.variant}
              >
                {coverageLabel(solution.coverage)}
              </Badge>
              <span className="text-xs text-muted-foreground">
                confidence {confidencePct(solution.confidence)}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

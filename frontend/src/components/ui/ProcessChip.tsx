"use client";

import { Badge } from "./Badge";
import { PROCESS_FAMILY_SWATCH, processFamily } from "./processFamily";
import { processIcon } from "../icons/processIcons";
import { cn } from "@/lib/utils";

interface ProcessChipProps {
  /** The canonical taxonomy id — what the swatch and the glyph are keyed by. */
  process: string;
  /** What the reader sees. Humanized by the caller, which owns the wording. */
  label: string;
  className?: string;
}

/**
 * One process, as a chip: family swatch, tool glyph, name.
 *
 * Shared rather than spelled at each card, because the swatch is only worth
 * anything while the same family is the same colour on every surface it
 * appears on — a card that draws its own would be a second legend.
 *
 * The swatch is a square with the world's own corner (`rounded-sm`), not a
 * pill-dot: the badge around it is cut with `--ttm-radius` for the same
 * reason, and in the squarer worlds a circle inside it reads as borrowed.
 *
 * `aria-hidden`, because it says nothing the label does not. Colour here
 * groups chips for an eye scanning a card; the process is named in text beside
 * it, so nothing is carried by hue alone.
 */
export function ProcessChip({ process, label, className }: ProcessChipProps) {
  const Icon = processIcon(process);
  const family = processFamily(process);

  return (
    <Badge variant="default" className={className}>
      <span className="inline-flex items-center gap-1.5">
        {family && (
          <span
            aria-hidden="true"
            className={cn(
              "h-2.5 w-2.5 shrink-0 rounded-sm",
              PROCESS_FAMILY_SWATCH[family],
            )}
          />
        )}
        {Icon && <Icon className="h-3.5 w-3.5 shrink-0" />}
        {label}
      </span>
    </Badge>
  );
}

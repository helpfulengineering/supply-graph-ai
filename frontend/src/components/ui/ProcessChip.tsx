"use client";

import { Badge } from "./Badge";
import { PROCESS_FAMILY_INK, processFamily } from "./processFamily";
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
 * One process, as a chip: the tool glyph in its family's colour, then the name.
 *
 * The glyph IS the swatch. This drew both for a while — a 10px coloured square
 * and then a monochrome glyph beside it — which put two marks in front of the
 * label where one would do, and made the colour read as a legend key rather
 * than as a property of the thing named. Painting the glyph says the same in
 * one mark, on the element a reader already looks at to tell a printer from a
 * mill.
 *
 * Shared rather than spelled at each card, because the colour is only worth
 * anything while the same family is the same hue on every surface it appears
 * on — a card that drew its own would be a second legend.
 *
 * The glyph is `aria-hidden`: it says nothing the label does not. Colour groups
 * chips for an eye scanning a card, and the process is named in text beside it,
 * so nothing is carried by hue alone.
 */
export function ProcessChip({ process, label, className }: ProcessChipProps) {
  const Icon = processIcon(process);
  const family = processFamily(process);

  return (
    <Badge variant="default" className={className}>
      <span className="inline-flex items-center gap-1.5">
        {Icon && (
          <Icon
            className={cn(
              "h-3.5 w-3.5 shrink-0",
              family && PROCESS_FAMILY_INK[family],
            )}
          />
        )}
        {label}
      </span>
    </Badge>
  );
}

"use client";

import { useId } from "react";
import {
  MARK_EDGES,
  MARK_NODES,
  MARK_OUTLINE,
  MARK_STROKE_WIDTH,
  MARK_VIEWBOX,
} from "./mark";

/**
 * The OHM mark, inline.
 *
 * Geometry comes from ./mark.ts, which the favicon generator reads too — the
 * two used to be hand-kept copies, and that is how the tab drifted away from
 * the app. What this version has that the file cannot is the live ramp: inline
 * in the document it resolves var(--ttm-irid-*), so the mark re-themes with
 * every world instead of freezing one of them.
 *
 * The gradient id is per-instance. Two logos in one document (header and
 * footer) sharing a literal id means the second definition wins and both marks
 * paint from it — same colours today, a silent bug the moment they differ.
 */
export function Logo({ className = "h-6 w-6" }: { className?: string }) {
  const gradientId = `ohm-mark-${useId()}`;
  const stroke = `url(#${gradientId})`;
  return (
    <svg
      viewBox={`0 0 ${MARK_VIEWBOX} ${MARK_VIEWBOX}`}
      className={className}
      role="img"
      aria-label="Open Hardware Manager"
      fill="none"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--ttm-irid-a)" />
          <stop offset="30%" stopColor="var(--ttm-irid-b)" />
          <stop offset="60%" stopColor="var(--ttm-irid-c)" />
          <stop offset="100%" stopColor="var(--ttm-irid-e)" />
        </linearGradient>
      </defs>

      <path
        d={MARK_OUTLINE}
        stroke={stroke}
        strokeWidth={MARK_STROKE_WIDTH}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d={MARK_EDGES}
        stroke={stroke}
        strokeWidth={MARK_STROKE_WIDTH}
        strokeLinecap="round"
      />
      {MARK_NODES.map((node) => (
        <circle
          key={`${node.cx},${node.cy}`}
          cx={node.cx}
          cy={node.cy}
          r={node.r}
          fill={stroke}
        />
      ))}
    </svg>
  );
}

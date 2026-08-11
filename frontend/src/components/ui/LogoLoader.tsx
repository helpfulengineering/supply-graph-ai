"use client";

import { useId } from "react";
import {
  MARK_EDGES,
  MARK_NODES,
  MARK_OUTLINE,
  MARK_STROKE_WIDTH,
  MARK_VIEWBOX,
} from "../layout/mark";

/**
 * The OHM mark, waiting.
 *
 * Every loading surface in the app drew a borrowed glyph — `Loader2` in
 * states.tsx, a hand-rolled arc in LoadingSpinner.tsx — so the one moment a
 * visitor spends staring at a single element was the one moment the product
 * showed them somebody else's shape. This draws the mark instead, from the
 * same `mark.ts` the favicon and the header logo read, and animates what the
 * mark already means: a highlight travelling the open nut while the design
 * node and the two maker nodes surface in the order the edges reach them.
 *
 * Geometry is not re-declared here — that is the whole point of mark.ts, and
 * re-typing the path data is exactly how the favicon once came adrift from the
 * app. Colour is not declared either: the gradient reads the live token ramp,
 * so the loader re-themes with every world.
 *
 * Decorative by construction. It is never the only thing on screen — callers
 * own the live region and the words in it (see LoadingState) — so announcing
 * "Open Hardware Manager" here would add a second, less useful voice to a
 * status a screen reader is already being told about.
 */
export function LogoLoader({ className = "h-9 w-9" }: { className?: string }) {
  // Per-instance, for the reason <Logo> gives: two marks in one document
  // sharing a literal id means the second definition wins for both.
  const gradientId = `ohm-loader-${useId()}`;
  const stroke = `url(#${gradientId})`;

  return (
    <svg
      viewBox={`0 0 ${MARK_VIEWBOX} ${MARK_VIEWBOX}`}
      className={className}
      aria-hidden="true"
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

      {/* The outline, held at a fraction so the travelling segment has a track
          to run on rather than appearing out of nothing. With motion reduced
          there is no travelling segment, so this becomes the whole outline. */}
      <path
        d={MARK_OUTLINE}
        stroke={stroke}
        strokeWidth={MARK_STROKE_WIDTH}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="opacity-25 motion-reduce:opacity-100"
      />
      {/* The travelling segment. Hidden rather than paused under reduced
          motion: `animate-none` would leave a fifth of the nut permanently
          brighter than the rest, which reads as a rendering fault. */}
      <path
        d={MARK_OUTLINE}
        pathLength={100}
        strokeDasharray="20 80"
        stroke={stroke}
        strokeWidth={MARK_STROKE_WIDTH}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="animate-mark-trace motion-reduce:hidden"
      />

      <path
        d={MARK_EDGES}
        stroke={stroke}
        strokeWidth={MARK_STROKE_WIDTH}
        strokeLinecap="round"
        className="opacity-40 motion-reduce:opacity-100"
      />

      {MARK_NODES.map((node, i) => (
        <circle
          key={`${node.cx},${node.cy}`}
          cx={node.cx}
          cy={node.cy}
          r={node.r}
          fill={stroke}
          // fill-box, or the scale would be taken about the viewBox origin and
          // throw each node off its own edge instead of pulsing in place.
          className="origin-center animate-mark-node [transform-box:fill-box] motion-reduce:animate-none"
          // The stagger is the mark's own reading order — design first, then
          // the makers — and is per-node data, so it belongs on the node
          // rather than in three near-identical keyframe rules.
          style={{ animationDelay: `${i * 180}ms` }}
        />
      ))}
    </svg>
  );
}

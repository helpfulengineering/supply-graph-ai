"use client";

import { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CAPTION } from "./typography";

/**
 * The app's tooltip.
 *
 * The app had no tooltip, so anything that needed one used `title` — which
 * cannot be styled, cannot be reached by keyboard, does not appear for touch,
 * and is announced inconsistently by screen readers. Every one of those is a
 * reason a label must not live only in a tooltip; a tooltip supplements a
 * visible control, it does not replace its name.
 *
 * Built on Base UI's tooltip (the same primitive library `button.tsx` uses) so
 * hover intent, focus, Escape-to-dismiss, and collision-aware placement are
 * the library's problem. Everything visual comes from the token layer, so it
 * re-themes with the rest of the app rather than carrying a private palette.
 */
export function Tooltip({
  content,
  value,
  side = "top",
  children,
}: {
  /** Supplementary text. Never the only place a control is named. */
  content: ReactNode;
  /**
   * The figure the label belongs to, drawn on its own row behind a dot.
   *
   * Borrowed from the chart tooltips deliberately: echarts already draws a
   * label over a dot-and-value row everywhere on the dashboard, and a second,
   * plainer tooltip a few hundred pixels away reads as a different app. One
   * shape for "here is what this is, and what it says".
   */
  value?: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  children: ReactNode;
}) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger render={<span className="inline-flex" />}>
        {children}
      </TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        {/*
          Tight to the trigger and pointing at it. At a comfortable offset and
          with no arrow, a tooltip beside a row of four cards is a floating
          label that could belong to any of them — the arrow is what makes it
          this card's.
        */}
        {/*
          Above the map. Leaflet's panes carry z-index up to 800 and its
          container creates no stacking context of its own, so they compete
          with this portal in the root context and win by default — the
          tooltip rendered behind the tiles. --z-overlay is the layer the
          drawer already uses for the same reason.
        */}
        <TooltipPrimitive.Positioner
          side={side}
          sideOffset={2}
          align="center"
          style={{ zIndex: "var(--z-overlay)" }}
        >
          <TooltipPrimitive.Popup
            className={cn(
              "max-w-64 rounded-lg border border-border bg-popover px-3 py-2 shadow-glow",
            )}
          >
            <TooltipPrimitive.Arrow
              className={cn(
                "data-[side=bottom]:top-[-5px] data-[side=bottom]:rotate-180",
                "data-[side=top]:bottom-[-5px]",
                "data-[side=left]:right-[-7px] data-[side=left]:rotate-90",
                "data-[side=right]:left-[-7px] data-[side=right]:-rotate-90",
              )}
            >
              <svg width="10" height="5" viewBox="0 0 10 5" aria-hidden="true">
                <path
                  d="M0 0 L5 5 L10 0"
                  className="fill-popover stroke-border"
                  strokeWidth="1"
                />
              </svg>
            </TooltipPrimitive.Arrow>
            <span className={cn(CAPTION, "block text-popover-foreground")}>
              {content}
            </span>
            {value !== undefined && (
              <span className="mt-1 flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="h-2 w-2 shrink-0 rounded-full bg-primary"
                />
                <span className="ml-auto text-sm font-semibold tabular-nums text-foreground">
                  {value}
                </span>
              </span>
            )}
          </TooltipPrimitive.Popup>
        </TooltipPrimitive.Positioner>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

/**
 * Wrap the app once so tooltips share hover-intent timing: the first opens
 * after a delay, and moving between neighbouring triggers opens the next
 * immediately rather than re-waiting.
 *
 * 120ms, not the 400 that seemed reasonable in the abstract. On a stat card
 * whose label lives only in the tooltip, four hundred milliseconds of nothing
 * reads as a tooltip that does not work — long enough to move the pointer on
 * and conclude the feature is broken. Short enough to feel attached to the
 * pointer, long enough not to fire while crossing a row of cards.
 */
export function TooltipProvider({ children }: { children: ReactNode }) {
  return (
    <TooltipPrimitive.Provider delay={120} closeDelay={80}>
      {children}
    </TooltipPrimitive.Provider>
  );
}

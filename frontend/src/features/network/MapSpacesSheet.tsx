"use client";

import Link from "next/link";
import { useEffect } from "react";
import { X } from "lucide-react";
import type { NetworkSpace } from "../../api/ohm/network";
import { NetworkSpaceCard } from "./NetworkSpaceCard";
import { CAPTION, SECTION_LABEL_SM } from "../../components/ui/typography";
import { cn } from "@/lib/utils";

/**
 * How many cards a region is allowed to draw.
 *
 * The map holds every space in memory and a zoomed-out viewport frames
 * thousands of them; a sheet that rendered all of them would pay the cost
 * NetworkMap deleted when it stopped mounting a React element per marker, and
 * pay it again on every pan. The cap is a reading limit as much as a budget —
 * nobody scrolls two thousand cards — so it is stated in the footer rather than
 * silently applied, with the two ways out beside it.
 */
const MAX_CARDS = 24;

interface MapSpacesSheetProps {
  /** The spaces the map currently frames. */
  spaces: NetworkSpace[];
  open: boolean;
  onClose: () => void;
}

/**
 * The spaces in the frame, as cards, without leaving the map.
 *
 * The dashboard map answered "where is the network" and nothing else: every
 * space was on it, none was named, and the only way to read one was to leave
 * the page. Clicking a marker gives a popup — one space, chosen by hitting a
 * 12px target among clusters. The sheet answers the question a pan actually
 * asks, which is about the region rather than about one point in it.
 *
 * The standard bottom sheet, one shape at every width: fixed to the viewport,
 * full-bleed, rising from the bottom edge of the screen with a grab bar at the
 * top. Cards lay out in a grid inside it, so the same component reads as a
 * stack on a phone and as a band across a desktop.
 *
 * Not a modal. It opens on a gesture the reader made for another reason
 * (dragging the map), so it must not trap focus, dim the page, or swallow the
 * next drag — panning with it open keeps updating it, which is the whole point.
 * Escape and the close button are the ways out.
 */
export function MapSpacesSheet({ spaces, open, onClose }: MapSpacesSheetProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  const shown = spaces.slice(0, MAX_CARDS);

  return (
    <aside
      aria-label="Spaces in view"
      aria-hidden={!open}
      className={cn(
        // Fixed to the viewport, not to the map. A sheet rises from the bottom
        // edge of the SCREEN; one parked inside the map's own box is a panel
        // wearing a sheet's clothes, and it inherits that box's clipping,
        // rounding and 440px of height as constraints on a surface that should
        // have none of them.
        // z-2000 and not the z-50 a sheet would normally take. The map card is
        // `relative` with `z-index: auto`, so it opens no stacking context of
        // its own and Leaflet's internal layers — 400 for the tile and marker
        // panes, 700 for popups, 800 and 1000 for the controls — are compared
        // against this element directly. At z-50 the sheet rose in front of the
        // page and behind the map it belongs to: cards under tiles, the footer
        // under the attribution. Above 1000 clears the lot; the toast layer at
        // 9999 still outranks it, which is correct.
        "fixed inset-x-0 bottom-0 z-[2000] flex max-h-[70svh] flex-col",
        "rounded-t-2xl border-t border-panel-border bg-card/95 shadow-2xl backdrop-blur-md",
        "pb-[env(safe-area-inset-bottom)]",
        "transition-transform duration-200 ease-out motion-reduce:transition-none",
        open ? "translate-y-0" : "pointer-events-none translate-y-full",
      )}
    >
      {open && (
        <>
          {/* The grab bar. It is not draggable — the sheet is dismissed by the
              button beside it or by Escape — but it is the mark that says
              "sheet" before any of the text is read. */}
          <div
            aria-hidden="true"
            className="mx-auto mt-2 h-1 w-9 shrink-0 rounded-full bg-border"
          />
          <div className="flex shrink-0 items-center justify-between gap-2 border-b border-panel-border px-4 py-2">
            <h2 className={SECTION_LABEL_SM}>
              {spaces.length === 0
                ? "Nothing in view"
                : `${spaces.length.toLocaleString()} space${spaces.length === 1 ? "" : "s"} in view`}
            </h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              title="Close"
              className="-mr-1 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <X aria-hidden="true" className="h-4 w-4" />
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-3">
            {spaces.length === 0 ? (
              <p className={CAPTION}>
                No spaces in this part of the map. Pan or zoom out.
              </p>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {shown.map((s) => (
                  <NetworkSpaceCard key={`${s.source}-${s.id}`} space={s} />
                ))}
              </div>
            )}
          </div>

          {spaces.length > shown.length && (
            <p
              className={cn(
                CAPTION,
                "shrink-0 border-t border-panel-border px-3 py-2",
              )}
            >
              Showing {shown.length} of {spaces.length.toLocaleString()}. Zoom
              in to narrow, or{" "}
              <Link href="/facilities?view=map" className="underline">
                browse them all
              </Link>
              .
            </p>
          )}
        </>
      )}
    </aside>
  );
}

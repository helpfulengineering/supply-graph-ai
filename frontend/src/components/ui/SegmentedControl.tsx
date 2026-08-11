"use client";

import { useRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface SegmentedOption<T extends string> {
  value: T;
  label: ReactNode;
  /** Announced instead of `label` when the visible text is an abbreviation. */
  srLabel?: string;
}

/**
 * A one-of-N choice rendered as a joined row of segments.
 *
 * There were three hand-rolled copies — the match page's system mode, the
 * network page's list/map toggle, and the create page's guided/JSON tabs —
 * with two different sets of ARIA and two different ideas of what the control
 * even is. All three were also unusable from the keyboard beyond Tab, which is
 * the part worth stating plainly rather than filing under "harmonisation":
 *
 * `role="radiogroup"` with `role="radio"` children is a promise. A screen
 * reader announces "1 of 3" and tells the user to press an arrow key, and the
 * arrow key did nothing — every segment sat in the tab order, and the group
 * had no key handling at all. That is worse than a plain group of buttons,
 * because the assistive technology has been told to expect a behaviour the
 * component does not implement.
 *
 * So this implements the WAI-ARIA radio group pattern properly:
 *
 *   - roving tabindex — the group is ONE tab stop, on the selected segment
 *   - Arrow keys move selection and focus together, wrapping at both ends
 *   - Home / End jump to first / last
 *
 * Selection follows focus, which is the pattern's specified behaviour for
 * radio groups and is right here because every option is cheap to preview.
 *
 * Layout: full width and evenly divided below `sm`, intrinsic width above it.
 * A three-segment control at intrinsic width leaves a phone with three small
 * targets huddled against the left margin; stretching them gives thumb-sized
 * hit areas and a row that reads as one control. Segments are `min-h-11` (44px)
 * on the small layout, matching the drawer's targets from Phase 4, and relax to
 * the denser desktop rhythm above `sm`.
 */
export function SegmentedControl<T extends string>({
  label,
  value,
  options,
  onChange,
  className,
}: {
  /** Accessible name for the group. */
  label: string;
  value: T;
  options: readonly SegmentedOption<T>[];
  onChange: (value: T) => void;
  className?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function move(delta: number) {
    const current = options.findIndex((o) => o.value === value);
    const from = current === -1 ? 0 : current;
    // Wrap, so the group has no dead end in either direction.
    const next = (from + delta + options.length) % options.length;
    onChange(options[next].value);
    refs.current[next]?.focus();
  }

  function select(index: number) {
    onChange(options[index].value);
    refs.current[index]?.focus();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    switch (e.key) {
      case "ArrowRight":
      case "ArrowDown":
        e.preventDefault();
        move(1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
        e.preventDefault();
        move(-1);
        break;
      case "Home":
        e.preventDefault();
        select(0);
        break;
      case "End":
        e.preventDefault();
        select(options.length - 1);
        break;
    }
  }

  const selectedIndex = options.findIndex((o) => o.value === value);

  return (
    <div
      role="radiogroup"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={cn(
        "flex w-full overflow-hidden rounded-lg border border-input sm:inline-flex sm:w-auto",
        className,
      )}
    >
      {options.map((o, i) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={active}
            // The roving tabindex. Exactly one segment is tabbable: the
            // selected one, or the first when nothing is selected yet — so the
            // group is a single stop in the tab order, as the pattern requires.
            tabIndex={active || (selectedIndex === -1 && i === 0) ? 0 : -1}
            onClick={() => onChange(o.value)}
            className={cn(
              "min-h-11 flex-1 px-3 text-sm font-medium transition-colors",
              "focus-visible:relative focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-ring",
              "sm:min-h-9 sm:flex-none",
              active
                ? "bg-primary text-primary-foreground"
                : "bg-background text-foreground hover:bg-accent",
            )}
          >
            {o.srLabel ? <span className="sr-only">{o.srLabel}</span> : null}
            <span aria-hidden={o.srLabel ? "true" : undefined}>{o.label}</span>
          </button>
        );
      })}
    </div>
  );
}

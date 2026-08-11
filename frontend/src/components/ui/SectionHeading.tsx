"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { SECTION_LABEL, SECTION_TITLE } from "./typography";

/**
 * A section heading that is also a destination.
 *
 * The help page grew this first and kept it to itself, so every other section
 * heading in the app was a heading you could not link to — the address bar
 * described the page but never the part of it being discussed.
 *
 * `scroll-mt` keeps the sticky header from covering the target when a
 * #fragment lands on it.
 */
export function SectionHeading({
  id,
  role = "title",
  className,
  children,
}: {
  id: string;
  /** Which heading role to render at — see components/ui/typography. */
  role?: "title" | "label";
  className?: string;
  children: ReactNode;
}) {
  return (
    <h2
      id={id}
      className={cn(
        role === "title" ? SECTION_TITLE : SECTION_LABEL,
        "group scroll-mt-20",
        className,
      )}
    >
      {/*
        inline-flex + min-h-6 so the permalink clears the 24x24 WCAG 2.5.8
        minimum. The anchor wraps the whole heading, so its accessible name is
        the heading text and 2.5.8's inline exception does not apply — there is
        no surrounding non-target text constraining it. At section-label scale
        the line box was 21px, and the only thing holding it there was the type
        scale, which is the author's choice and therefore the author's problem.
      */}
      <a
        href={`#${id}`}
        className="inline-flex min-h-6 items-center no-underline hover:text-foreground"
      >
        {children}
        <span
          aria-hidden="true"
          className="ml-2 opacity-0 transition-opacity group-hover:opacity-60 group-focus-within:opacity-60"
        >
          #
        </span>
        <span className="sr-only"> — link to this section</span>
      </a>
    </h2>
  );
}

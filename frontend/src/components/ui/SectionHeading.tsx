"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CARD_TITLE, SECTION_LABEL, SECTION_TITLE } from "./typography";

/** Heading scales this can render at — see components/ui/typography. */
const ROLE_CLASS = {
  title: SECTION_TITLE,
  label: SECTION_LABEL,
  card: CARD_TITLE,
} as const;

/**
 * A section heading that is also a destination.
 *
 * The help page grew this first and kept it to itself, so every other section
 * heading in the app was a heading you could not link to — the address bar
 * described the page but never the part of it being discussed.
 *
 * `scroll-mt` keeps the sticky header from covering the target when a
 * #fragment lands on it. It is the one offset for every anchor in the app: a
 * hero crumb pointing at a panel and a permalink pointing at its heading are
 * the same journey, and two spellings of the clearance would land them at two
 * different heights on the same page.
 *
 * `card` exists so a panel heading can become a destination without being
 * resized into a section heading. The operator panels are the case — their
 * crumb names all three, and adopting this at `title` scale would have grown
 * every one of them to make a link work.
 */
export function SectionHeading({
  id,
  role = "title",
  className,
  children,
}: {
  id: string;
  role?: keyof typeof ROLE_CLASS;
  className?: string;
  children: ReactNode;
}) {
  return (
    <h2 id={id} className={cn(ROLE_CLASS[role], "group scroll-mt-20", className)}>
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

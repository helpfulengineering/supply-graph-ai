"use client";

import type { ReactNode } from "react";
import { SiteHeader } from "./SiteHeader";
import { SiteFooter } from "./SiteFooter";
import { AuthBanner } from "../../features/auth/AuthBanner";

export function Layout({ children }: { children: ReactNode }) {
  /*
   * No background on the root element. `body` already paints `bg-background`,
   * and on top of it the blueprint grid that index.css calls "paper the page
   * sits on" — fixed to the viewport, drawn from each world's own border
   * colour. This div is `min-h-screen`, so repeating the background colour on
   * it laid an opaque sheet over the full height of that paper and the grid
   * was visible nowhere in the app. Removing it changes no colour: the value
   * underneath is the same token.
   */
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground focus:not-sr-only focus:absolute focus:left-4 focus:top-3"
      >
        Skip to content
      </a>
      <SiteHeader />
      <AuthBanner />
      {/* Gutters match the header's, which they did not: the bar stepped in at
          px-4 on phones while the page below it stepped in at px-6, so the
          mark and every h1 under it sat on two different left edges until the
          viewport hit 640px. One rhythm, set here and in SiteFooter. */}
      {/*
        A sheet over the paper, not a lid on it.

        The grid is a ground, and a ground with body copy sitting directly on
        it is just a busy page: every caption, crumb and loose line of text was
        competing with a ruling running underneath it. So the content column
        gets its own surface — but at 55%, not 100%. Opaque would have put the
        grid back where it started, visible nowhere except the outer gutters,
        and gone entirely on a phone where this column is the full width.

        At that share the ruling reads as texture under the sheet and at full strength
        around it, which is the difference between paper the page sits on and
        paper the page is printed over. Same colour as `body`, so this occludes
        rather than tints — no world gains a surface it did not choose.
      */}
      <main
        id="main"
        className="mx-auto w-full max-w-7xl flex-1 bg-background/55 px-4 py-5 sm:px-6"
      >
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}

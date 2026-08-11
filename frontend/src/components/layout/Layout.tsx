"use client";

import type { ReactNode } from "react";
import { SiteHeader } from "./SiteHeader";
import { SiteFooter } from "./SiteFooter";
import { AuthBanner } from "../../features/auth/AuthBanner";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
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
      <main
        id="main"
        className="mx-auto w-full max-w-7xl flex-1 px-4 py-5 sm:px-6"
      >
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}

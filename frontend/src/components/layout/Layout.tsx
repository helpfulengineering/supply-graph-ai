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
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}

"use client";

import type { ReactNode } from "react";
import { NavBar } from "./NavBar";
import { AuthBanner } from "../../features/auth/AuthBanner";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <AuthBanner />
      <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
    </div>
  );
}

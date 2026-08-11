"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, Moon, Sun } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import { NavDrawer } from "./NavDrawer";
import { useKeyboardShortcuts } from "../../hooks/useKeyboardShortcuts";
import { DemoDataBadge } from "../../features/dashboard/DemoDataBadge";
import { Logo } from "./Logo";

/**
 * The universal header, in the TTM chrome idiom: a slim bar that carries the
 * wordmark and the tools cluster, and nothing else. Every page's own h1 is
 * its identity; all navigation is consolidated in the hamburger sitemap.
 */
export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { isDark, toggle } = useTheme();

  useKeyboardShortcuts({
    menuOpen,
    openMenu: () => setMenuOpen(true),
    closeMenu: () => setMenuOpen(false),
  });

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-card shadow-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Mark only. The bar carries no wordmark because every page's hero
            states its own identity — on the dashboard the two would sit one
            above the other saying the same words. */}
        <Link href="/" className="flex items-center no-underline">
          <Logo className="h-7 w-7" />
          <span className="sr-only">Open Hardware Manager — home</span>
        </Link>

        <div className="flex items-center gap-2">
          <DemoDataBadge />

          <button
            type="button"
            onClick={toggle}
            aria-pressed={isDark}
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
            title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            className="flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            {isDark ? (
              <Sun aria-hidden="true" className="h-5 w-5" />
            ) : (
              <Moon aria-hidden="true" className="h-5 w-5" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setMenuOpen(true)}
            aria-label="Site menu"
            aria-keyshortcuts="?"
            aria-expanded={menuOpen}
            aria-controls="site-menu"
            aria-haspopup="dialog"
            className="flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <Menu aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>
      </div>

      <NavDrawer open={menuOpen} onClose={() => setMenuOpen(false)} />
    </header>
  );
}

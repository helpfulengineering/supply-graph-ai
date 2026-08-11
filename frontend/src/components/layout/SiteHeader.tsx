"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, Moon, Sun } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import { NavDrawer } from "./NavDrawer";

/**
 * The universal header, in the TTM chrome idiom: a slim bar that carries the
 * wordmark and the tools cluster, and nothing else. Every page's own h1 is
 * its identity; all navigation is consolidated in the hamburger sitemap.
 */
export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { isDark, toggle } = useTheme();

  return (
    <header className="sticky top-0 z-40 bg-card shadow-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link
          href="/"
          className="flex items-baseline gap-2 no-underline"
        >
          <span className="text-lg font-bold tracking-tight text-primary-ink">
            OHM
          </span>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            Open Hardware Manager
          </span>
          <span className="sr-only">home</span>
        </Link>

        <div className="flex items-center gap-1">
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
            aria-expanded={menuOpen}
            aria-controls="site-menu"
            aria-haspopup="dialog"
            className="flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <Menu aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* The TTM brand signature: an iridescent pearl rule closing the bar.
          Pure decoration, pure tokens — the five --ttm-irid-* stops come from
          the token file, so worlds can retune it. Static (no shimmer): motion
          stays inside the reduced-motion guard, and a permanent animation
          would break the axe settling contract. */}
      <div
        aria-hidden="true"
        className="h-0.5 w-full"
        style={{
          background:
            "linear-gradient(90deg, var(--ttm-irid-a), var(--ttm-irid-b), var(--ttm-irid-c), var(--ttm-irid-d), var(--ttm-irid-e))",
        }}
      />
      <NavDrawer open={menuOpen} onClose={() => setMenuOpen(false)} />
    </header>
  );
}

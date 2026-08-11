"use client";

import { useCallback, useState } from "react";
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

  // Stable, because the drawer's focus trap keys its effect on this callback:
  // an inline arrow made every header render a teardown and rebuild of the
  // trap, which moves focus. See lib/useDialogFocus.
  const openMenu = useCallback(() => setMenuOpen(true), []);
  const closeMenu = useCallback(() => setMenuOpen(false), []);

  useKeyboardShortcuts({ menuOpen, openMenu, closeMenu });

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-card/90 shadow-sm backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Mark only. The bar carries no wordmark because every page's hero
            states its own identity — on the dashboard the two would sit one
            above the other saying the same words.
            The hover lift is a transition rather than an animation: the axe
            helper waits for animations to settle before each of the twenty
            theme-matrix scans, so nothing here may run on its own. */}
        <Link
          href="/"
          className="-ml-1.5 flex h-11 w-11 items-center justify-center rounded-md no-underline transition-transform hover:scale-105 motion-reduce:transition-none motion-reduce:hover:scale-100"
        >
          <Logo className="h-7 w-7" />
          <span className="sr-only">Open Hardware Manager — home</span>
        </Link>

        {/* The two icon buttons carry 44px targets with their glyphs at 20px,
            so they already hold 12px of their own padding on each side — a
            gap between them lands as a visible hole. The badge, which has no
            such padding, gets its own margin instead. */}
        <div className="flex items-center gap-0">
          <span className="mr-2 empty:mr-0">
            <DemoDataBadge />
          </span>

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
            onClick={openMenu}
            aria-label="Site menu"
            aria-keyshortcuts="?"
            aria-expanded={menuOpen}
            aria-controls="site-menu"
            aria-haspopup="dialog"
            className="-mr-1.5 flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <Menu aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>
      </div>

      <NavDrawer open={menuOpen} onClose={closeMenu} />
    </header>
  );
}

"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "../context/ThemeContext";
import { CHORD_MS, CHORD_ROUTES, isTypingTarget } from "../components/layout/shortcuts";

interface Options {
  menuOpen: boolean;
  openMenu: () => void;
  closeMenu: () => void;
}

/**
 * Site-wide keyboard layer: `?` menu, `t` theme, `m` mode, `g`+key to navigate.
 *
 * Bound on document at the bubble phase, not capture. The reference used
 * capture to outrank page handlers, but here the drawer owns Escape and its
 * own focus trap; intercepting before it would take Escape away from the
 * dialog, which is a WCAG expectation rather than a preference.
 *
 * Every branch checks isTypingTarget first, so typing "t" into a search box
 * never re-themes the page.
 */
export function useKeyboardShortcuts({ menuOpen, openMenu, closeMenu }: Options): void {
  const router = useRouter();
  const { toggle, theme, setTheme, themes } = useTheme();

  // Refs so the listener can stay mounted for the life of the app: rebinding
  // on every theme change would drop a chord that was mid-flight.
  const state = useRef({ menuOpen, openMenu, closeMenu, toggle, theme, setTheme, themes });
  state.current = { menuOpen, openMenu, closeMenu, toggle, theme, setTheme, themes };

  useEffect(() => {
    let armedAt = 0;

    const onKeyDown = (event: KeyboardEvent) => {
      if (isTypingTarget(event)) return;
      const s = state.current;

      if (event.key === "?") {
        event.preventDefault();
        if (s.menuOpen) s.closeMenu();
        else s.openMenu();
        return;
      }

      const armed = armedAt !== 0 && Date.now() - armedAt < CHORD_MS;
      if (armed && CHORD_ROUTES[event.key]) {
        event.preventDefault();
        armedAt = 0;
        s.closeMenu();
        router.push(CHORD_ROUTES[event.key]);
        return;
      }

      if (event.key === "g") {
        event.preventDefault();
        armedAt = Date.now();
        return;
      }
      armedAt = 0;

      if (event.key === "t") {
        event.preventDefault();
        const order = s.themes.map((t) => t.slug);
        const next = order[(order.indexOf(s.theme) + 1) % order.length];
        s.setTheme(next);
        return;
      }
      if (event.key === "m") {
        event.preventDefault();
        s.toggle();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    // Observable bind marker: keys pressed before hydration land nowhere, so
    // tests (and anything else scripting the page) need a signal that the
    // listener exists rather than a guess at hydration timing.
    document.documentElement.dataset.keysReady = "true";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      delete document.documentElement.dataset.keysReady;
    };
  }, [router]);
}

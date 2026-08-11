"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Theme controller: a world (`data-ttm-theme`) and a mode (`.dark`).
 *
 * The two are orthogonal on purpose — ten worlds x two polarities is twenty
 * looks from one dimension of state each, and mode stays the `.dark` class so
 * every existing Tailwind `dark:` utility keeps working (see the selector note
 * in styles/tokens.css).
 *
 * Mode follows the OS until the visitor picks one, then their choice sticks.
 * That is the whole precedence chain today; an instance-level default arrives
 * with the optional site layer, which slots in between the two.
 */

const MODE_KEY = "ohm-color-scheme";
const THEME_KEY = "ohm-theme";

export const THEMES = [
  { slug: "ttm", label: "Warm" },
  { slug: "terminal", label: "Terminal" },
  { slug: "zine", label: "Zine" },
  { slug: "ocean", label: "Ocean" },
  { slug: "forest", label: "Forest" },
  { slug: "synthwave", label: "Synthwave" },
  { slug: "ember", label: "Ember" },
  { slug: "mono", label: "Mono" },
  { slug: "blueprint", label: "Blueprint" },
  { slug: "bubblegum", label: "Bubblegum" },
] as const;

export type ThemeSlug = (typeof THEMES)[number]["slug"];

export const DEFAULT_THEME: ThemeSlug = "ttm";

const SLUGS: readonly string[] = THEMES.map((t) => t.slug);

export function isThemeSlug(value: string | null): value is ThemeSlug {
  return value !== null && SLUGS.includes(value);
}

function read(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(key);
  } catch {
    // localStorage unavailable (private browsing, etc.) — fall through
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

function getInitialDark(): boolean {
  if (typeof window === "undefined") return false;
  const shared = fromUrl().dark;
  if (shared !== undefined) return shared;
  const stored = read(MODE_KEY);
  if (stored !== null) return stored === "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/**
 * ?theme= and ?mode= let a link carry the look it was seen in — the whole
 * point of shipping twenty variants is that people show each other one.
 *
 * A URL parameter outranks stored preference (the sender is stating the
 * subject of the link) and then persists, so the recipient keeps it and the
 * parameter is not needed again.
 */
function fromUrl(): { theme?: ThemeSlug; dark?: boolean } {
  if (typeof window === "undefined") return {};
  const params = new URLSearchParams(window.location.search);
  const theme = params.get("theme");
  const mode = params.get("mode");
  return {
    theme: isThemeSlug(theme) ? theme : undefined,
    dark: mode === "dark" ? true : mode === "light" ? false : undefined,
  };
}

function getInitialTheme(): ThemeSlug {
  const shared = fromUrl().theme;
  if (shared) return shared;
  const stored = read(THEME_KEY);
  return isThemeSlug(stored) ? stored : DEFAULT_THEME;
}

export interface ThemeController {
  isDark: boolean;
  toggle: () => void;
  theme: ThemeSlug;
  setTheme: (theme: ThemeSlug) => void;
  themes: typeof THEMES;
  /** The current page URL carrying this look, for sharing. */
  shareUrl: () => string;
}

export function useDarkMode(): ThemeController {
  const [isDark, setIsDark] = useState<boolean>(getInitialDark);
  const [theme, setThemeState] = useState<ThemeSlug>(getInitialTheme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
    write(MODE_KEY, isDark ? "dark" : "light");
  }, [isDark]);

  useEffect(() => {
    document.documentElement.setAttribute("data-ttm-theme", theme);
    write(THEME_KEY, theme);
  }, [theme]);

  // Track the OS until the visitor states a preference; after that their
  // choice is the answer and system changes are ignored.
  useEffect(() => {
    if (read(MODE_KEY) !== null) return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => setIsDark(e.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const setTheme = useCallback((next: ThemeSlug) => setThemeState(next), []);
  const toggle = useCallback(() => setIsDark((d) => !d), []);

  const shareUrl = useCallback(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("theme", theme);
    url.searchParams.set("mode", isDark ? "dark" : "light");
    return url.toString();
  }, [theme, isDark]);

  return { isDark, toggle, theme, setTheme, themes: THEMES, shareUrl };
}

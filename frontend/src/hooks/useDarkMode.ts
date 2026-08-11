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

  /**
   * Paint first, re-render second.
   *
   * Both of these used to be a bare `setState`, which made the visible colour
   * change wait on React: the effects above are what write `data-ttm-theme`
   * and `.dark`, and an effect runs only after the render that scheduled it
   * has committed. So every consumer of this context re-rendered before the
   * browser was allowed to repaint — the map rebuilding three thousand
   * markers, the charts re-resolving their tokens, the picker probing all ten
   * worlds — and the measurement on /match against the real catalogue was a
   * 949ms long task with four more behind it. The attribute flipped at 31ms
   * and then nothing could paint for over a second: press a key, watch the old
   * world sit there, press it again.
   *
   * Writing the attribute here, in the event handler, is the whole fix for
   * what the eye sees. It is a pure style recalc with no React in it, so the
   * new world paints on the next frame instead of behind the render.
   *
   * The state update stays URGENT, deliberately. It was a transition for one
   * revision, which did let the browser paint — and left the radio the visitor
   * had just clicked showing its old selection until the deferred pass landed,
   * which is the same complaint one level down: the control that registers the
   * action has to register it. The expense is not this string propagating, it
   * is the three hooks that re-resolve palettes from it, and those defer
   * themselves — see `useDeferredValue` in chartTokens, useSourceColors and
   * useThemeSwatches.
   *
   * The effects above stay: they are what applies a theme that arrived from
   * somewhere other than a click — the OS media query, the URL parameter, the
   * initial mount — and they are a no-op write when the DOM already agrees.
   */
  const setTheme = useCallback((next: ThemeSlug) => {
    document.documentElement.setAttribute("data-ttm-theme", next);
    write(THEME_KEY, next);
    setThemeState(next);
  }, []);

  const toggle = useCallback(() => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    write(MODE_KEY, next ? "dark" : "light");
    setIsDark(next);
  }, []);

  const shareUrl = useCallback(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("theme", theme);
    url.searchParams.set("mode", isDark ? "dark" : "light");
    return url.toString();
  }, [theme, isDark]);

  return { isDark, toggle, theme, setTheme, themes: THEMES, shareUrl };
}

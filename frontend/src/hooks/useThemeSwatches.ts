"use client";

import { useEffect, useState } from "react";
import { THEMES, type ThemeSlug } from "./useDarkMode";

export interface ThemeSwatch {
  /** The world's call-to-action accent, resolved to a concrete colour. */
  accent: string;
  /** The world's sans stack. Terminal and Mono repoint it at the mono face. */
  fontSans: string;
}

/**
 * Each world's own accent and typeface, resolved from the live token values.
 *
 * The theme picker listed ten names in identical type, so choosing a world
 * meant picking a word and seeing what happened. The names should carry the
 * thing they name.
 *
 * Getting those values is the interesting part. Every world block in
 * tokens.css is anchored to `:root` — deliberately, because specificity is
 * load-bearing there: `.dark` is (0,1,0) and a world block has to outrank it,
 * which the file documents at length. That anchor means a world's palette is
 * only reachable while that world is the active one on <html>, so a swatch
 * cannot be read from a nested element carrying the attribute, and dropping
 * the `:root` to allow it would reintroduce exactly the bug the file warns
 * about.
 *
 * A per-world colour map in CSS would work and is the obvious alternative. It
 * would also be ten duplicated colours free to drift from the palettes they
 * claim to preview, which is the one thing the token layer exists to prevent.
 *
 * So the values are read the way `chartTokens.ts` reads its own: from the live
 * document. Each world is applied to <html>, its resolved values are read
 * back, and the original is restored — all synchronously within one task, so
 * no intermediate state is ever painted. Nothing is duplicated, a palette edit
 * is reflected with no second place to update, and a new world in THEMES gets
 * a swatch with no code change at all.
 */
export function resolveThemeSwatches(): Record<ThemeSlug, ThemeSwatch> {
  const root = document.documentElement;
  const original = root.getAttribute("data-ttm-theme");
  const out = {} as Record<ThemeSlug, ThemeSwatch>;

  try {
    for (const { slug } of THEMES) {
      root.setAttribute("data-ttm-theme", slug);
      // getComputedStyle forces the style recalc, so the read below sees this
      // world and not the one that was set a moment ago.
      const style = getComputedStyle(root);
      out[slug] = {
        accent: style.getPropertyValue("--ttm-accent-cta").trim(),
        fontSans: style.getPropertyValue("--ttm-font-sans").trim(),
      };
    }
  } finally {
    // Restore in a finally: a throw mid-loop would otherwise strand the whole
    // app in whichever world the loop had reached.
    if (original === null) root.removeAttribute("data-ttm-theme");
    else root.setAttribute("data-ttm-theme", original);
  }

  return out;
}

/**
 * Swatches, resolved once on mount.
 *
 * Not `useMemo` during render: this reads and writes documentElement, which is
 * a side effect and would run during React's render phase. It also cannot run
 * on the server, and the swatches do not depend on the active world — a
 * world's own accent is the same colour whichever world is currently applied.
 *
 * Empty until the effect runs, so callers fall back to unstyled dots for one
 * paint rather than rendering a wrong colour.
 */
export function useThemeSwatches(): Partial<Record<ThemeSlug, ThemeSwatch>> {
  const [swatches, setSwatches] = useState<
    Partial<Record<ThemeSlug, ThemeSwatch>>
  >({});

  // Polarity is deliberately not a dependency. A world's accent is defined in
  // both its light and dark blocks, so the swatch reads whichever polarity is
  // live — which is the honest preview, since that is what the visitor would
  // actually get by choosing it.
  useEffect(() => {
    setSwatches(resolveThemeSwatches());
  }, []);

  return swatches;
}

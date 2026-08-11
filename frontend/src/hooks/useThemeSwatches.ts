"use client";

import { useDeferredValue, useEffect, useState } from "react";
import { useTheme } from "../context/ThemeContext";
import { THEMES, type ThemeSlug } from "./useDarkMode";
import { formatRgb, inkFor, parseRgb } from "../lib/contrastInk";

export interface ThemeSwatch {
  /** The world's call-to-action accent, resolved to a concrete colour. */
  accent: string;
  /**
   * The same accent, corrected for use AS TEXT on the drawer's surface.
   *
   * Raw accents are not safe as ink: several worlds' sit between 3.8:1 and
   * 4.5:1, which is the finding behind --color-primary-ink in Phase 3. This
   * blends toward the CURRENT world's foreground — the drawer is painted in
   * the active world, not the one being previewed — so the correction matches
   * the surface the text actually lands on.
   *
   * Solved for the RATIO, not fixed at 80%: a fixed blend of a pale accent is
   * still pale, which is why Mono and Bubblegum were unreadable in light mode
   * while passing every check that only looked at the active world's own
   * tokens. See lib/contrastInk.
   */
  ink: string;
  /**
   * That world's OWN card surface, so the row can be painted in it.
   *
   * The differentiator, and the reason this field exists. Ten worlds do not
   * have ten accents: Warm, Zine, Terminal, Synthwave and Bubblegum all land
   * on a magenta, so a picker that tinted only the name drew five rows in the
   * same colour and the reader had to choose between them by word alone. What
   * those worlds do not share is their ground — cream, near-black, ink-blue —
   * which is most of what a world looks like and none of what the picker was
   * showing.
   */
  ground: string;
  /** That world's border, so the chip has an edge in its own palette. */
  edge: string;
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

  // A probe, because the ratio has to be computed from CONCRETE colours and
  // the tokens are authored as hex, var() chains, and color-mix(). Setting each
  // one as a `color` and reading it back makes the browser do the resolving,
  // and what ships to React is an rgb() string either way.
  const probe = document.createElement("span");
  probe.style.display = "none";
  root.appendChild(probe);
  const resolve = (value: string): string => {
    probe.style.color = "";
    probe.style.color = value;
    return getComputedStyle(probe).color;
  };

  try {
    for (const { slug } of THEMES) {
      root.setAttribute("data-ttm-theme", slug);
      // getComputedStyle forces the style recalc, so the read below sees this
      // world and not the one that was set a moment ago.
      const style = getComputedStyle(root);
      const accent = style.getPropertyValue("--ttm-accent-cta").trim();
      const accentRgb = parseRgb(resolve(accent));
      const textRgb = parseRgb(
        resolve(style.getPropertyValue("--ttm-text").trim()),
      );
      // Each world's own card, not the active one's. The row is now painted in
      // the world it names, so the ink has to clear AA against that world's
      // ground rather than against the drawer's — otherwise a pale accent that
      // was legible on the current surface goes invisible on its own.
      const ground = resolve(style.getPropertyValue("--card").trim());
      const groundRgb = parseRgb(ground);
      out[slug] = {
        accent,
        ground,
        edge: resolve(style.getPropertyValue("--border").trim()),
        ink:
          accentRgb && textRgb && groundRgb
            ? formatRgb(inkFor(accentRgb, textRgb, groundRgb))
            : accent,
        fontSans: style.getPropertyValue("--ttm-font-sans").trim(),
      };
    }
  } finally {
    probe.remove();
    // Restore in a finally: a throw mid-loop would otherwise strand the whole
    // app in whichever world the loop had reached.
    if (original === null) root.removeAttribute("data-ttm-theme");
    else root.setAttribute("data-ttm-theme", original);
  }

  return out;
}

/**
 * Swatches, re-resolved whenever the surface under them changes.
 *
 * Not `useMemo` during render: this reads and writes documentElement, which is
 * a side effect and would run during React's render phase, and it cannot run
 * on the server at all.
 *
 * Keyed on the active world AND polarity, which the first version deliberately
 * did not do — on the reasoning that a world's accent is the same colour
 * whichever world is applied. True of the accent, false of the ink: the ink is
 * solved against the surface it lands on, so a set resolved in dark mode is
 * wrong the moment the visitor switches to light. That is exactly how Mono
 * stayed unreadable — its near-white accent needs no correction on a dark card
 * and needs a large one on a cream card, and nothing re-ran to apply it.
 *
 * Empty until the effect runs, so callers fall back to unstyled names for one
 * paint rather than rendering a wrong colour.
 */
export function useThemeSwatches(
  /**
   * Whether the picker is actually on screen.
   *
   * `resolveThemeSwatches` applies each of the ten worlds to <html> and reads
   * the result back, which forces ten full style recalculations. That is a fair
   * price for drawing the picker and a pure waste when the drawer is closed —
   * which is most of the time, and is exactly when someone presses `t` or `m`
   * from the page. Ungated it ran on every theme change whether or not anything
   * was there to show, and put ten recalcs on the critical path of a keystroke
   * whose entire job is to repaint quickly.
   */
  enabled = true,
): Partial<Record<ThemeSlug, ThemeSwatch>> {
  const { theme: urgentTheme, isDark: urgentDark } = useTheme();
  // Deferred, so a theme change repaints before it re-resolves.
  //
  // This hook re-reads palettes and re-renders whatever draws from them, and
  // on a page with a full facility catalogue that measured as a 949ms task
  // sitting between the keystroke and the paint. `useDeferredValue` lets React
  // render the cheap consumers — the picker's own radio, the chrome — at once
  // and come back for this at lower priority, so the world changes colour
  // immediately and the canvases catch up a frame or two later. Nothing here
  // is what a visitor is waiting to see.
  const theme = useDeferredValue(urgentTheme);
  const isDark = useDeferredValue(urgentDark);
  const [swatches, setSwatches] = useState<
    Partial<Record<ThemeSlug, ThemeSwatch>>
  >({});

  useEffect(() => {
    if (!enabled) return;
    // After the frame, not during the effect pass. The polarity class lands on
    // <html> in the PROVIDER's effect, and React runs a child's effects before
    // its parent's — so resolving here directly reads the surface the app is
    // leaving rather than the one it is entering, and every ink comes out
    // solved against the wrong background. That is the whole bug: toggling to
    // light left ten labels between 1.05:1 and 3.18:1.
    const frame = requestAnimationFrame(() =>
      setSwatches(resolveThemeSwatches()),
    );
    return () => cancelAnimationFrame(frame);
  }, [theme, isDark, enabled]);

  return swatches;
}

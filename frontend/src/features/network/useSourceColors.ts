"use client";

import { useEffect, useState } from "react";
import { useTheme } from "../../context/ThemeContext";
import { sourceColor, unplottedColor } from "./networkSummary";
import { tileFilter } from "./tileFilter";

export interface SourceColors {
  local: string;
  mom: string;
  unplotted: string;
  /** CSS `filter` putting the raster tiles in this world's colour. */
  tiles: string;
}

function resolve(): SourceColors {
  const root =
    typeof window === "undefined"
      ? null
      : getComputedStyle(document.documentElement);
  return {
    local: sourceColor("local"),
    mom: sourceColor("mom"),
    unplotted: unplottedColor(),
    tiles: tileFilter({
      accent: root?.getPropertyValue("--ttm-accent-cta").trim() ?? "",
      // The polarity the document is actually in, not the hook's `isDark`:
      // the class is what the tiles are being composited against.
      isDark: root
        ? document.documentElement.classList.contains("dark")
        : false,
    }),
  };
}

/**
 * The map's colours, re-read after the world changes.
 *
 * `sourceColor` reads the live documentElement, so calling it during render
 * returns the palette the app is LEAVING: `data-ttm-theme` and the `.dark`
 * class are written by `useDarkMode`'s effects, which run after the render that
 * would consume them. The legend kept the previous world's dots until something
 * else forced a re-render, and the map kept the previous world's markers until
 * the space set changed.
 *
 * Same shape as `lib/chartTokens`, and for the same reason — that one put every
 * axis label at roughly 2:1 after a single theme switch. Resolved once during
 * render so the first paint is correct (the inline theme script writes the
 * world before React mounts), then again a frame after any change.
 */
export function useSourceColors(): SourceColors {
  const { theme, isDark } = useTheme();
  const [colors, setColors] = useState<SourceColors>(resolve);

  // Urgent, and no longer deferred. The defer was here because a theme change
  // used to rebuild every marker on the map from these values — the reason the
  // map turned a beat after the rest of the page. The markers now recolour
  // from the cascade (see `sourceVar`), so what is left is one filter string
  // for the tile layer, cached per world: cheap enough to land in the same
  // commit as everything else, which is what "at once" has to mean.
  useEffect(() => {
    const key = `${theme}|${isDark ? "dark" : "light"}`;
    const cached = CACHE.get(key);
    if (cached) {
      setColors(cached);
      return;
    }
    // Still after the frame: the polarity class lands on <html> in the
    // provider's effect, and a child's effects run before its parent's.
    const frame = requestAnimationFrame(() => {
      const next = resolve();
      CACHE.set(key, next);
      setColors(next);
    });
    return () => cancelAnimationFrame(frame);
  }, [theme, isDark]);

  return colors;
}

const CACHE = new Map<string, SourceColors>();

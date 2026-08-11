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

  useEffect(() => {
    const frame = requestAnimationFrame(() => setColors(resolve()));
    return () => cancelAnimationFrame(frame);
  }, [theme, isDark]);

  return colors;
}

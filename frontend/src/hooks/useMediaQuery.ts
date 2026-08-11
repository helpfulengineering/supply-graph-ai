"use client";

import { useEffect, useState } from "react";

/**
 * Live answer to a media query.
 *
 * For the cases a CSS breakpoint cannot reach: the charts paint to canvas, so
 * "drop the axis on a phone" is a decision the component has to make in JS
 * rather than a utility it can hang off `sm:`.
 *
 * Starts false so the server and the first client render agree — a layout that
 * differs between the two is a hydration mismatch, and the narrow case is the
 * one that can afford a frame of the wide default rather than the reverse.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

/** The `sm:` breakpoint, as a question a component can ask. */
export const NARROW = "(max-width: 639px)";

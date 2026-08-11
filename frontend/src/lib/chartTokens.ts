"use client";

import { useMemo } from "react";
import { useTheme } from "../context/ThemeContext";

/**
 * Runtime-resolved design tokens for canvas renderers.
 *
 * echarts and cytoscape paint to <canvas>, which cannot evaluate var() — they
 * need concrete colour strings. DOM surfaces should keep using the utilities;
 * this hook exists only for the two canvas libraries, resolving the bridge
 * tokens from the live document so every world and polarity feeds the same
 * values the rest of the page renders with.
 */

export interface ChartTokens {
  series: [string, string, string, string, string];
  text: string;
  textMuted: string;
  textFaint: string;
  border: string;
  card: string;
  background: string;
  ring: string;
}

function read(style: CSSStyleDeclaration, name: string): string {
  return style.getPropertyValue(name).trim();
}

export function resolveChartTokens(): ChartTokens {
  const style = getComputedStyle(document.documentElement);
  return {
    series: [
      read(style, "--chart-1"),
      read(style, "--chart-2"),
      read(style, "--chart-3"),
      read(style, "--chart-4"),
      read(style, "--chart-5"),
    ],
    text: read(style, "--foreground"),
    textMuted: read(style, "--muted-foreground"),
    textFaint: read(style, "--ttm-text-faint"),
    border: read(style, "--border"),
    card: read(style, "--card"),
    background: read(style, "--background"),
    ring: read(style, "--ring"),
  };
}

/**
 * Tokens re-resolved whenever the world or polarity changes. The theme effects
 * write documentElement synchronously before paint, and this memo keys on the
 * same state they consume, so a theme switch re-renders every chart with the
 * new world's palette.
 */
export function useChartTokens(): ChartTokens {
  const { theme, isDark } = useTheme();
  // eslint-disable-next-line react-hooks/exhaustive-deps -- theme/isDark are proxies for the documentElement state the resolver reads
  return useMemo(() => resolveChartTokens(), [theme, isDark]);
}

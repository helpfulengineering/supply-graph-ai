"use client";

import { useMemo } from "react";
import { useTheme } from "../context/ThemeContext";
import { formatRgb, inkFor, parseRgb } from "./contrastInk";

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
  /** The caption rung of the type scale, in px — canvas wants a number. */
  fontSizeCaption: number;
}

function read(style: CSSStyleDeclaration, name: string): string {
  return style.getPropertyValue(name).trim();
}

/**
 * A type-scale rung as a pixel number.
 *
 * Same reason as the colours: a canvas cannot evaluate var(), so every chart
 * had picked its own literal — 11 here, 11 there, next to a DOM caption the
 * scale had already sized. Resolved against the root font size so a reader who
 * has enlarged their browser text gets larger chart labels too, which a
 * hardcoded 11 never gave them.
 */
function readFontSize(style: CSSStyleDeclaration, name: string): number {
  const rem = parseFloat(read(style, name));
  const root = parseFloat(getComputedStyle(document.documentElement).fontSize);
  return Math.round(rem * (root || 16));
}

export function resolveChartTokens(): ChartTokens {
  const style = getComputedStyle(document.documentElement);
  const card = read(style, "--card");

  /**
   * Label colours, corrected against the surface they are painted on.
   *
   * --muted-foreground and --ttm-text-faint are recessive by design and they
   * are safe where the DOM uses them: under a heading, beside a control, at
   * the size and weight the scale gives them. An axis label is neither — it is
   * the only name a bar has, and in Synthwave the muted purple on the panel's
   * navy left the country names barely visible.
   *
   * The axe matrix never caught it because a canvas has no text to scan: the
   * chart is one <canvas> element as far as any DOM checker is concerned. So
   * the ratio is enforced here, where the values are chosen, rather than
   * trusted to a gate that structurally cannot see them.
   */
  const legible = (value: string): string => {
    const ink = parseRgb(resolveColor(value));
    const surface = parseRgb(resolveColor(card));
    const text = parseRgb(resolveColor(read(style, "--foreground")));
    if (!ink || !surface || !text) return value;
    return formatRgb(inkFor(ink, text, surface));
  };

  return {
    series: [
      read(style, "--chart-1"),
      read(style, "--chart-2"),
      read(style, "--chart-3"),
      read(style, "--chart-4"),
      read(style, "--chart-5"),
    ],
    text: read(style, "--foreground"),
    textMuted: legible(read(style, "--muted-foreground")),
    textFaint: legible(read(style, "--ttm-text-faint")),
    border: read(style, "--border"),
    card,
    background: read(style, "--background"),
    ring: read(style, "--ring"),
    fontSizeCaption: readFontSize(style, "--ttm-fs-caption"),
  };
}

/**
 * A token value as a concrete `rgb()`, whatever it was authored as — hex, a
 * var() chain, a color-mix(). The browser is the only correct parser for that,
 * so it does the work.
 */
function resolveColor(value: string): string {
  const probe = document.createElement("span");
  probe.style.display = "none";
  probe.style.color = value;
  document.documentElement.appendChild(probe);
  const resolved = getComputedStyle(probe).color;
  probe.remove();
  return resolved;
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

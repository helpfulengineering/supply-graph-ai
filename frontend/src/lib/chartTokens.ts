"use client";

import { useEffect, useState } from "react";
import { useTheme } from "../context/ThemeContext";
import { formatRgb, inkFor, parseRgb } from "./contrastInk";

/** Contrast floor for chart labels — above AA; see `legible` in the resolver. */
const CHART_LABEL_CONTRAST = 7;

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
   *
   * Solved to 7:1, not the 4.5 AA asks of body text. These are the smallest
   * type in the app, sitting against bars rather than flat ground, and a label
   * that technically clears AA still reads as fog at this size — Ocean dark's
   * faint rung is 2.7:1 raw and was not legible corrected to 4.5 either. The
   * headroom costs a little saturation on a colour that carried no meaning.
   */
  const legible = (value: string): string => {
    const ink = parseRgb(resolveColor(value));
    const surface = parseRgb(resolveColor(card));
    const text = parseRgb(resolveColor(read(style, "--foreground")));
    if (!ink || !surface || !text) return value;
    return formatRgb(inkFor(ink, text, surface, CHART_LABEL_CONTRAST));
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
 * Tokens re-resolved whenever the world or polarity changes.
 *
 * In an effect, after a frame — not a `useMemo` during render, which is what
 * this was and which resolved the OUTGOING world every time. `data-ttm-theme`
 * and the `.dark` class are written by `useDarkMode`'s effects, and effects run
 * after the render that recomputed the memo, so every chart read the palette
 * the app was leaving. Measured across the twenty variants: one theme switch
 * put every axis label at roughly 2:1, and it stayed there until a reload.
 *
 * The initial value is resolved during render on purpose: the inline theme
 * script has already written the world onto documentElement before React
 * mounts, so the first read is correct and the charts do not paint once in the
 * wrong palette before the effect lands.
 */
export function useChartTokens(): ChartTokens {
  const { theme, isDark } = useTheme();
  const [tokens, setTokens] = useState<ChartTokens>(resolveChartTokens);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setTokens(resolveChartTokens()));
    return () => cancelAnimationFrame(frame);
  }, [theme, isDark]);

  return tokens;
}

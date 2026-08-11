"use client";

import ReactECharts from "echarts-for-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useChartTokens } from "../../lib/chartTokens";
import { NARROW, useMediaQuery } from "../../hooks/useMediaQuery";
import {
  BODY_MUTED,
  CAPTION,
  CARD_TITLE,
} from "../../components/ui/typography";
import { PANEL } from "../../components/ui/surface";
import { cn } from "@/lib/utils";
import type { Row } from "./networkStats";

interface NetworkBarChartProps {
  title: string;
  caption: string;
  rows: Row[];
  /** Which of the world's five chart colours to draw in. */
  seriesIndex?: number;
  /** Where a bar leads. Given, the chart becomes a set of links into the network. */
  hrefFor?: (row: Row) => string;
  /** Plural noun for the rows ("countries"), for the keyboard list's summary. */
  noun?: string;
  /**
   * What to say when there is nothing to chart, and why.
   *
   * Required rather than optional, because the default this replaces was
   * `return null` — the card removed itself from the page. On a dashboard whose
   * two charts sit in a two-column grid that left one card beside a blank
   * column and no clue that a second one had ever existed: "What it can make"
   * vanished whenever the facilities on an instance carried no manufacturing
   * processes, which is the ordinary state of a fresh instance and of the
   * seeded demo world.
   *
   * A missing card cannot be read as "nothing to show yet", only as something
   * broken or, worse, as nothing at all. Making the caller supply the sentence
   * means each chart says which data is absent and what would fill it, rather
   * than sharing one shrug.
   */
  empty: string;
}

/** Pixels per row: the bar, its label, and the gap that keeps them legible. */
const ROW_HEIGHT = 24;
/** How much chart is on screen before the panel scrolls rather than grows. */
const VIEWPORT_HEIGHT = 288;

/**
 * Scroll surfaces inside a card. The thin, tokenised bar keeps a full country
 * list from hanging a bright default scrollbar down the side of a dark panel;
 * `overscroll-contain` keeps a flick that bottoms out from scrolling the page.
 */
const SCROLLABLE =
  "overflow-y-auto overscroll-contain [scrollbar-width:thin] [scrollbar-color:var(--ttm-scrollbar-thumb)_var(--ttm-scrollbar-track)]";

/** echarts hands back the series item or the axis label, depending on what was hit. */
interface ChartClick {
  componentType?: string;
  dataIndex?: number;
  value?: unknown;
}

/**
 * A horizontal bar chart for the dashboard's derived stats.
 *
 * Horizontal because every category here is a name — countries, capabilities —
 * and names read straight rather than rotated 45 degrees under a vertical axis.
 *
 * echarts paints to canvas and cannot evaluate var(), so colours come from
 * useChartTokens: the same values the DOM around it renders with, for whichever
 * of the twenty variants is active.
 *
 * Every category is drawn, not a top slice: the tail is where a reader finds
 * their own country. The chart therefore grows past the panel and the panel
 * scrolls — a fixed viewport, tight against the card, over a full-height chart.
 */
export function NetworkBarChart({
  title,
  caption,
  rows,
  seriesIndex = 0,
  hrefFor,
  noun = "rows",
  empty,
}: NetworkBarChartProps) {
  const t = useChartTokens();
  const narrow = useMediaQuery(NARROW);
  const router = useRouter();

  // Ascending, because echarts' y-axis runs bottom-up: the largest bar ends up
  // at the top, where a reader starts.
  const ordered = [...rows].reverse();
  const colour = t.series[seriesIndex % t.series.length];

  const option = {
    backgroundColor: "transparent",
    textStyle: { color: t.textMuted },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: t.card,
      borderColor: t.border,
      textStyle: { color: t.text },
    },
    grid: { left: 8, right: 28, top: 8, bottom: 4, containLabel: true },
    // No gridlines at any width. Every bar ends in its own number, so the
    // lines add no precision — they only cross the bars and the value labels,
    // which is the one thing a reader is actually looking at. The axis itself
    // goes on a phone too, where its ticks collide into an unreadable run.
    xAxis: {
      type: "value",
      show: !narrow,
      splitLine: { show: false },
      axisLabel: { color: t.textFaint },
    },
    yAxis: {
      type: "category",
      data: ordered.map((r) => r.label),
      axisLabel: {
        color: t.textMuted,
        width: narrow ? 96 : 130,
        overflow: "truncate",
      },
      axisLine: { lineStyle: { color: t.border } },
      axisTick: { show: false },
      // The name is as much a target as the bar it belongs to.
      triggerEvent: Boolean(hrefFor),
    },
    series: [
      {
        type: "bar",
        data: ordered.map((r) => r.value),
        itemStyle: { color: colour, borderRadius: [0, 3, 3, 0] },
        barMaxWidth: 18,
        label: {
          show: true,
          position: "right",
          color: t.textMuted,
          fontSize: t.fontSizeCaption,
        },
        cursor: hrefFor ? "pointer" : "default",
      },
    ],
    // Off: a permanently-running animation would keep the axe helper waiting
    // for it to settle on every one of the twenty theme-matrix scans.
    animation: false,
  };

  const onClick = (params: ChartClick) => {
    if (!hrefFor) return;
    const row =
      params.componentType === "yAxis"
        ? ordered.find((r) => r.label === params.value)
        : ordered[params.dataIndex ?? -1];
    if (row) router.push(hrefFor(row));
  };

  const chartHeight = Math.max(140, rows.length * ROW_HEIGHT);

  // The card keeps its heading, its caption, and its place in the grid; only
  // the chart is replaced. Same rhythm as the panel beside it, so a reader
  // comparing the two sees one answer and one absence rather than a layout
  // that changed shape.
  if (rows.length === 0) {
    return (
      <section className={PANEL} aria-label={title}>
        <h3 className={CARD_TITLE}>{title}</h3>
        <p className={cn(BODY_MUTED, "mt-0.5 mb-2 min-h-12")}>{caption}</p>
        <p className={cn(CAPTION, "py-6 text-center")}>{empty}</p>
      </section>
    );
  }

  return (
    <section className={PANEL} aria-label={title}>
      <h3 className={CARD_TITLE}>{title}</h3>
      {/*
        Two lines reserved whether or not the caption needs them, measured
        rather than guessed: at this rung two lines are 48px, and reserving 40
        left the wrapped caption 8px taller than its neighbour. Side by side
        these wrap differently — one line for "Facilities by country", two for
        "Facilities offering each capability" — which put the charts, and the
        links under them, on different baselines.
      */}
      <p className={cn(BODY_MUTED, "mt-0.5 mb-2 min-h-12")}>
        {caption}
        {hrefFor && " · select a bar to filter the network"}
      </p>
      {/*
        Focusable because it scrolls: a keyboard-only reader has to be able to
        reach the overflow, and a scroll container that cannot take focus is a
        region they can never move.
      */}
      <div
        className={cn(
          SCROLLABLE,
          "rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
        style={{ maxHeight: VIEWPORT_HEIGHT }}
        tabIndex={0}
        role="group"
        aria-label={`${title}, scrollable chart`}
      >
        <ReactECharts
          option={option}
          style={{ height: chartHeight }}
          /*
            SVG, not canvas. A canvas chart is one opaque element to every
            accessibility checker there is — the axe matrix scans twenty theme
            variants and cannot see a single label inside it, which is how
            unreadable axis text survived every gate the app has. As SVG the
            labels are real text: scannable, selectable, and they scale with
            browser zoom.
          */
          opts={{ renderer: "svg" }}
          onEvents={hrefFor ? { click: onClick } : undefined}
          notMerge
        />
      </div>
      {/*
        The chart is a canvas: a pointer can hit a bar, a keyboard cannot. The
        same rows as links, closed by default so they cost one tab stop rather
        than one per country — and open, they are the only reading of the
        figures a screen reader gets.
      */}
      {hrefFor && (
        <details className="mt-2">
          <summary
            className={cn(
              CAPTION,
              "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
          >
            All {rows.length.toLocaleString()} {noun} as links
          </summary>
          <ul className={cn(SCROLLABLE, "mt-1 max-h-48 space-y-0.5 text-sm")}>
            {rows.map((r) => (
              <li key={r.key}>
                {/*
                  A 24px line box, not the 18px the type scale gives this rung.
                  These are standalone list rows rather than links inside a
                  sentence, so WCAG 2.5.8's inline exception does not cover
                  them — the narrow-viewport lane measures them and it is
                  right to.
                */}
                <Link
                  href={hrefFor(r)}
                  className="flex min-h-6 items-center text-muted-foreground underline-offset-2 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {r.label}: {r.value.toLocaleString()}
                </Link>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

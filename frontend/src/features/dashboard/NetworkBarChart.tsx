"use client";

import ReactECharts from "echarts-for-react";
import { useChartTokens } from "../../lib/chartTokens";
import { CARD_TITLE } from "../../components/ui/typography";
import { PANEL } from "../../components/ui/surface";
import { BODY_MUTED } from "../../components/ui/typography";
import { cn } from "@/lib/utils";
import type { Row } from "./networkStats";

interface Props {
  title: string;
  caption: string;
  rows: Row[];
  /** Which of the world's five chart colours to draw in. */
  seriesIndex?: number;
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
 */
export function NetworkBarChart({ title, caption, rows, seriesIndex = 0 }: Props) {
  const t = useChartTokens();
  if (rows.length === 0) return null;

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
    grid: { left: 4, right: 24, top: 8, bottom: 4, containLabel: true },
    xAxis: {
      type: "value",
      splitLine: { lineStyle: { color: t.border } },
      axisLabel: { color: t.textFaint },
    },
    yAxis: {
      type: "category",
      data: ordered.map((r) => r.label),
      axisLabel: { color: t.textMuted, width: 130, overflow: "truncate" },
      axisLine: { lineStyle: { color: t.border } },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        data: ordered.map((r) => r.value),
        itemStyle: { color: colour, borderRadius: [0, 3, 3, 0] },
        barMaxWidth: 18,
        label: { show: true, position: "right", color: t.textMuted, fontSize: 11 },
      },
    ],
    // Off: a permanently-running animation would keep the axe helper waiting
    // for it to settle on every one of the twenty theme-matrix scans.
    animation: false,
  };

  return (
    <section className={PANEL} aria-label={title}>
      <h3 className={CARD_TITLE}>{title}</h3>
      <p className={cn(BODY_MUTED, "mt-0.5")}>{caption}</p>
      <ReactECharts
        option={option}
        style={{ height: Math.max(140, ordered.length * 28) }}
        opts={{ renderer: "canvas" }}
        notMerge
      />
    </section>
  );
}

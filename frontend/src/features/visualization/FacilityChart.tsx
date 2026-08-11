import ReactECharts from "echarts-for-react";
import { useChartTokens } from "../../lib/chartTokens";
import type { VisualizationData } from "../../types/supply-tree";
import { CARD_TITLE } from "../../components/ui/typography";

interface Props {
  data: VisualizationData;
}

export function FacilityChart({ data }: Props) {
  // echarts paints to canvas and cannot evaluate var(), so the tokens are
  // resolved to concrete values — the same ones the DOM around it renders
  // with, for whichever of the twenty variants is active.
  const t = useChartTokens();
  const distribution = data.network.facility_distribution;

  if (distribution.length === 0) {
    return null;
  }

  const facilities = distribution.map((d) => d.facility_name);
  const counts = distribution.map((d) => d.tree_count);
  const maxCount = Math.max(...counts, 1);

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
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: {
      type: "value",
      max: maxCount + 0.5,
      splitLine: { lineStyle: { color: t.border } },
      axisLabel: {
        color: t.textFaint,
        formatter: (v: number) => (Number.isInteger(v) ? String(v) : ""),
      },
    },
    yAxis: {
      type: "category",
      data: facilities,
      axisLabel: {
        color: t.textMuted,
        width: 180,
        overflow: "truncate",
      },
      axisLine: { lineStyle: { color: t.border } },
    },
    series: [
      {
        name: "Facilities",
        type: "bar",
        data: counts,
        barMaxWidth: 40,
        itemStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: t.series[0] },
              { offset: 1, color: t.series[1] },
            ],
          },
          borderRadius: [0, 4, 4, 0],
        },
        label: {
          show: true,
          position: "right",
          color: t.textMuted,
          fontSize: 11,
        },
      },
    ],
  };

  const chartHeight = Math.max(160, distribution.length * 48 + 40);

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="border-b border-border px-5 py-3">
        <h3 className={CARD_TITLE}>Facility Distribution</h3>
        <p className="text-xs text-muted-foreground">
          Trees assigned per facility
        </p>
      </div>
      <div className="p-4">
        <ReactECharts
          option={option}
          style={{ height: `${chartHeight}px`, width: "100%" }}
          opts={{ renderer: "svg" }}
          notMerge
        />
      </div>
    </div>
  );
}

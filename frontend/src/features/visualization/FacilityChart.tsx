import ReactECharts from "echarts-for-react";
import { useTheme } from "../../context/ThemeContext";
import type { VisualizationData } from "../../types/supply-tree";

interface Props {
  data: VisualizationData;
}

export function FacilityChart({ data }: Props) {
  const { isDark } = useTheme();
  const distribution = data.network.facility_distribution;

  if (distribution.length === 0) {
    return null;
  }

  const facilities = distribution.map((d) => d.facility_name);
  const counts = distribution.map((d) => d.tree_count);
  const maxCount = Math.max(...counts, 1);

  const option = {
    backgroundColor: "transparent",
    textStyle: { color: isDark ? "#94a3b8" : "#475569" },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: isDark ? "#1e293b" : "#ffffff",
      borderColor: isDark ? "#334155" : "#e2e8f0",
      textStyle: { color: isDark ? "#e2e8f0" : "#1e293b" },
    },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: {
      type: "value",
      max: maxCount + 0.5,
      splitLine: { lineStyle: { color: isDark ? "#1e293b" : "#f1f5f9" } },
      axisLabel: { color: isDark ? "#64748b" : "#94a3b8", formatter: (v: number) => (Number.isInteger(v) ? String(v) : "") },
    },
    yAxis: {
      type: "category",
      data: facilities,
      axisLabel: {
        color: isDark ? "#94a3b8" : "#475569",
        width: 180,
        overflow: "truncate",
      },
      axisLine: { lineStyle: { color: isDark ? "#334155" : "#e2e8f0" } },
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
            x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: "#6366f1" },
              { offset: 1, color: "#0ea5e9" },
            ],
          },
          borderRadius: [0, 4, 4, 0],
        },
        label: {
          show: true,
          position: "right",
          color: isDark ? "#94a3b8" : "#475569",
          fontSize: 11,
        },
      },
    ],
  };

  const chartHeight = Math.max(160, distribution.length * 48 + 40);

  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-100 px-5 py-3 dark:border-slate-800">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          Facility Distribution
        </h3>
        <p className="text-xs text-slate-400 dark:text-slate-500">
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

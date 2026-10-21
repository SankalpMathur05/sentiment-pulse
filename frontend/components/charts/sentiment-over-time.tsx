"use client";

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { formatBucket } from "@/lib/format";
import { SENTIMENTS } from "@/lib/sentiment";
import type { AnalyticsSummary, Sentiment } from "@/lib/types";
import { SENTIMENT_CHART_CONFIG } from "./sentiment-donut";

const AXIS_LABEL = { className: "fill-muted-foreground text-[11px]" };

// Recharts sorts legend and tooltip items alphabetically by default; keep the app-wide order.
const sentimentOrder = (item: { dataKey?: unknown }) =>
  SENTIMENTS.indexOf(item.dataKey as Sentiment);

/**
 * Predictions per time bucket, stacked by sentiment. Bars rather than areas: each
 * bucket is a discrete count, and a single bucket still renders as something visible.
 * Neutral is stacked between the two poles so positive and negative never touch.
 */
export function SentimentOverTime({
  timeseries,
  granularity,
}: Pick<AnalyticsSummary, "timeseries" | "granularity">) {
  const rows = timeseries.map((bucket) => ({
    ...bucket,
    label: formatBucket(bucket.bucket, granularity),
  }));

  return (
    <ChartContainer config={SENTIMENT_CHART_CONFIG} className="aspect-auto h-72 w-full">
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 16, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          minTickGap={24}
          label={{
            ...AXIS_LABEL,
            value: granularity === "hour" ? "Hour (UTC)" : "Day (UTC)",
            position: "insideBottom",
            offset: -12,
          }}
        />
        <YAxis
          allowDecimals={false}
          tickLine={false}
          axisLine={false}
          width={44}
          label={{
            ...AXIS_LABEL,
            value: "Predictions",
            angle: -90,
            position: "insideLeft",
            style: { textAnchor: "middle" },
          }}
        />
        <ChartTooltip
          cursor={{ fill: "var(--muted)", opacity: 0.6 }}
          itemSorter={sentimentOrder}
          content={<ChartTooltipContent />}
        />
        <ChartLegend
          verticalAlign="top"
          itemSorter={sentimentOrder}
          content={<ChartLegendContent />}
        />
        {SENTIMENTS.map((sentiment, i) => (
          <Bar
            key={sentiment}
            dataKey={sentiment}
            stackId="sentiment"
            fill={`var(--color-${sentiment})`}
            maxBarSize={28}
            stroke="var(--card)"
            strokeWidth={1}
            radius={i === SENTIMENTS.length - 1 ? [4, 4, 0, 0] : 0}
          />
        ))}
      </BarChart>
    </ChartContainer>
  );
}

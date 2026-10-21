"use client";

import { Pie, PieChart } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { formatNumber, formatPercent } from "@/lib/format";
import { SENTIMENT_STYLES, SENTIMENTS } from "@/lib/sentiment";
import type { Sentiment } from "@/lib/types";

export const SENTIMENT_CHART_CONFIG = Object.fromEntries(
  SENTIMENTS.map((s) => [
    s,
    { label: SENTIMENT_STYLES[s].label, color: SENTIMENT_STYLES[s].color },
  ]),
) satisfies ChartConfig;

/** Share of each sentiment, with the total in the centre and a value legend beside it. */
export function SentimentDonut({ counts }: { counts: Record<Sentiment, number> }) {
  const total = SENTIMENTS.reduce((sum, s) => sum + (counts[s] ?? 0), 0);
  const data = SENTIMENTS.map((sentiment) => ({
    sentiment,
    count: counts[sentiment] ?? 0,
    fill: `var(--color-${sentiment})`,
  }));

  return (
    <div className="grid items-center gap-6 sm:grid-cols-[auto_minmax(0,1fr)]">
      <div className="relative mx-auto size-44">
        <ChartContainer config={SENTIMENT_CHART_CONFIG} className="aspect-square size-full">
          <PieChart>
            <ChartTooltip content={<ChartTooltipContent hideLabel nameKey="sentiment" />} />
            <Pie
              data={data}
              dataKey="count"
              nameKey="sentiment"
              innerRadius="70%"
              outerRadius="100%"
              startAngle={90}
              endAngle={-270}
              // A 2px ring in the card colour separates the segments.
              stroke="var(--card)"
              strokeWidth={2}
            />
          </PieChart>
        </ChartContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-semibold tracking-tight">{formatNumber(total)}</span>
          <span className="text-xs text-muted-foreground">{total === 1 ? "post" : "posts"}</span>
        </div>
      </div>

      <ul className="grid gap-3">
        {data.map(({ sentiment, count }) => {
          const { label, icon: Icon, fillClass } = SENTIMENT_STYLES[sentiment];
          return (
            <li key={sentiment} className="flex items-center gap-2.5 text-sm">
              <span className={`size-2.5 shrink-0 rounded-[3px] ${fillClass}`} aria-hidden />
              <Icon className="size-4 text-muted-foreground" aria-hidden />
              <span>{label}</span>
              <span className="ml-auto font-mono text-xs text-muted-foreground tabular-nums">
                {formatNumber(count)}
              </span>
              <span className="w-14 text-right font-medium tabular-nums">
                {formatPercent(total ? count / total : null)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

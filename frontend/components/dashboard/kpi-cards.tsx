import { Gauge, Layers, Zap } from "lucide-react";
import { StatCard } from "@/components/common/stat-card";
import { Card } from "@/components/ui/card";
import { formatCount, formatNumber, formatPercent } from "@/lib/format";
import { countsBySentiment, SENTIMENT_STYLES, SENTIMENTS } from "@/lib/sentiment";
import type { AnalyticsSummary } from "@/lib/types";

const GRID = "grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6";

export function KpiCards({ summary }: { summary: AnalyticsSummary }) {
  const counts = countsBySentiment(summary.distribution);

  return (
    <div className={GRID}>
      <StatCard
        icon={Layers}
        label="Total analysed"
        value={formatNumber(summary.total)}
        sub={formatCount(summary.unique_texts, "unique post")}
      />
      {SENTIMENTS.map((sentiment) => {
        // Shares are computed from the counts, so they always agree with the total shown.
        const share = summary.total ? counts[sentiment] / summary.total : 0;
        const { label, icon, fillClass } = SENTIMENT_STYLES[sentiment];
        return (
          <StatCard
            key={sentiment}
            icon={icon}
            label={label}
            value={formatPercent(share)}
            sub={formatCount(counts[sentiment], "post")}
            meter={{ value: share, className: fillClass }}
          />
        );
      })}
      <StatCard
        icon={Gauge}
        label="Avg confidence"
        value={formatPercent(summary.average_confidence)}
        sub={`${formatNumber(summary.low_confidence_count)} low-confidence`}
      />
      <StatCard
        icon={Zap}
        label="Cache hit rate"
        value={formatPercent(summary.cache.hit_rate)}
        sub={[
          formatCount(summary.cache.hit, "hit"),
          formatCount(summary.cache.miss, "miss", "misses"),
          summary.cache.bypass > 0 && `${formatNumber(summary.cache.bypass)} bypassed`,
        ]
          .filter(Boolean)
          .join(" · ")}
      />
    </div>
  );
}

export function KpiCardsSkeleton() {
  return (
    <div className={GRID} aria-hidden>
      {Array.from({ length: 6 }, (_, i) => (
        <Card key={i} size="sm" className="h-[104px] animate-pulse bg-muted/40" />
      ))}
    </div>
  );
}

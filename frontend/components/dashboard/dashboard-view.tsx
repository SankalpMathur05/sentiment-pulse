"use client";

import { useQuery } from "@tanstack/react-query";
import { ChartNoAxesColumn, RotateCw } from "lucide-react";
import { SentimentDonut } from "@/components/charts/sentiment-donut";
import { SentimentOverTime } from "@/components/charts/sentiment-over-time";
import { RelativeTime } from "@/components/common/relative-time";
import { ErrorState } from "@/components/feedback/error-state";
import { NoPredictions } from "@/components/feedback/no-predictions";
import { FilterBar } from "@/components/filters/filter-bar";
import { PageContainer, PageIntro } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useFilters } from "@/hooks/use-filters";
import { describeError } from "@/lib/errors";
import { EMPTY_FILTERS, hasActiveFilters } from "@/lib/filters";
import { summaryQuery } from "@/lib/queries";
import { countsBySentiment } from "@/lib/sentiment";
import type { AnalyticsSummary } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CachePanel } from "./cache-panel";
import { KpiCards, KpiCardsSkeleton } from "./kpi-cards";
import { RecentPredictions } from "./recent-predictions";

export function DashboardView() {
  const { filters, setFilters } = useFilters();
  const summary = useQuery(summaryQuery(filters, { live: true }));

  let content: React.ReactNode;
  if (summary.isPending) {
    content = <DashboardSkeleton />;
  } else if (summary.error && !summary.data) {
    content = (
      <ErrorState
        error={summary.error}
        onRetry={() => summary.refetch()}
        retrying={summary.isFetching}
      />
    );
  } else if (summary.data.total === 0) {
    content = (
      <NoPredictions
        filtered={hasActiveFilters(filters)}
        onResetFilters={() => setFilters(EMPTY_FILTERS)}
        icon={ChartNoAxesColumn}
        description="Analyze your first post and the dashboard will start filling in."
      />
    );
  } else {
    content = (
      // While new filters load, keep the previous numbers visible but dimmed.
      <div
        className={cn("grid gap-6 transition-opacity", summary.isPlaceholderData && "opacity-60")}
      >
        {summary.error && (
          <StaleDataNotice
            error={summary.error}
            updatedAt={summary.dataUpdatedAt}
            onRetry={() => summary.refetch()}
          />
        )}
        <KpiCards summary={summary.data} />
        <Charts summary={summary.data} />
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <CachePanel stored={summary.data.cache} />
          </div>
          <div className="min-w-0 lg:col-span-3">
            <RecentPredictions filters={filters} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <PageContainer>
      <PageIntro>
        Sentiment across every stored prediction. Updates every 20 seconds and when you return to
        the tab.
      </PageIntro>
      <FilterBar isRefreshing={summary.isFetching && !summary.isPending} />
      {content}
    </PageContainer>
  );
}

function Charts({ summary }: { summary: AnalyticsSummary }) {
  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Sentiment distribution</CardTitle>
          <CardDescription>Share of all predictions in this view.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-1 items-center">
          <div className="w-full">
            <SentimentDonut counts={countsBySentiment(summary.distribution)} />
          </div>
        </CardContent>
      </Card>
      <Card className="min-w-0 lg:col-span-3">
        <CardHeader>
          <CardTitle>Sentiment over time</CardTitle>
          <CardDescription>
            Predictions per {summary.granularity}, stacked by sentiment.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SentimentOverTime timeseries={summary.timeseries} granularity={summary.granularity} />
        </CardContent>
      </Card>
    </div>
  );
}

/** Shown when a background refresh fails but older data is still on screen. */
function StaleDataNotice({
  error,
  updatedAt,
  onRetry,
}: {
  error: unknown;
  updatedAt: number;
  onRetry: () => void;
}) {
  const { title } = describeError(error);
  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-warning/10 px-3 py-2 text-sm text-warning-ink ring-1 ring-warning/30 ring-inset"
    >
      <p>
        {title}. Showing data from <RelativeTime iso={new Date(updatedAt).toISOString()} />.
      </p>
      <Button variant="ghost" size="sm" onClick={onRetry}>
        <RotateCw />
        Retry
      </Button>
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="grid gap-6" aria-busy aria-label="Loading dashboard">
      <KpiCardsSkeleton />
      <div className="grid gap-6 lg:grid-cols-5">
        <Skeleton className="h-80 rounded-xl lg:col-span-2" />
        <Skeleton className="h-80 rounded-xl lg:col-span-3" />
      </div>
      <div className="grid gap-6 lg:grid-cols-5">
        <Skeleton className="h-72 rounded-xl lg:col-span-2" />
        <Skeleton className="h-72 rounded-xl lg:col-span-3" />
      </div>
    </div>
  );
}

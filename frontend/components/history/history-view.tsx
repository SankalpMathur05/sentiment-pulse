"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Download, History, SearchX } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { NoPredictions } from "@/components/feedback/no-predictions";
import { TableSkeleton } from "@/components/feedback/table-skeleton";
import { FilterBar } from "@/components/filters/filter-bar";
import { PageContainer, PageIntro } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useFilters } from "@/hooks/use-filters";
import { useSearchParamsUpdater } from "@/hooks/use-search-params-updater";
import { downloadCsv, predictionsToCsv } from "@/lib/csv";
import { EMPTY_FILTERS, hasActiveFilters } from "@/lib/filters";
import { formatCount, formatNumber } from "@/lib/format";
import { predictionsQuery } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { PredictionSheet } from "./prediction-sheet";
import { PredictionsTable } from "./predictions-table";

const PAGE_SIZE = 20;

export function HistoryView() {
  const searchParams = useSearchParams();
  const updateSearchParams = useSearchParamsUpdater();
  const { filters, setFilters } = useFilters();

  const page = Math.max(1, Number.parseInt(searchParams.get("page") ?? "", 10) || 1);
  const selectedId = searchParams.get("prediction");

  const { data, error, isPending, isFetching, isPlaceholderData, refetch } = useQuery(
    predictionsQuery(filters, page, PAGE_SIZE),
  );

  function goToPage(next: number) {
    updateSearchParams({ page: next > 1 ? String(next) : null });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const items = data?.items ?? [];
  // "Showing 21–40 of 312" (only rendered when the page has items).
  const first = data ? (data.page - 1) * data.page_size + 1 : 0;
  const last = first + items.length - 1;

  let content: React.ReactNode;
  if (isPending) {
    content = <TableSkeleton rows={10} />;
  } else if (error && !data) {
    content = (
      <ErrorState
        error={error}
        onRetry={() => refetch()}
        retrying={isFetching}
        className="m-4 w-auto"
      />
    );
  } else if (data.total === 0) {
    content = (
      <NoPredictions
        filtered={hasActiveFilters(filters)}
        onResetFilters={() => setFilters(EMPTY_FILTERS)}
        icon={History}
        description="Analyze your first post and it will be listed here."
        className="m-4 w-auto"
      />
    );
  } else if (items.length === 0) {
    content = (
      <EmptyState
        icon={SearchX}
        title={`There is no page ${page}`}
        description={`These filters have ${formatCount(data.pages, "page")} of results.`}
        className="m-4 w-auto"
        action={
          <Button variant="outline" size="sm" onClick={() => goToPage(1)}>
            Go to the first page
          </Button>
        }
      />
    );
  } else {
    content = (
      <div className={cn("transition-opacity", isPlaceholderData && "opacity-60")}>
        <PredictionsTable
          items={items}
          selectedId={selectedId}
          onSelect={(id) => updateSearchParams({ prediction: id })}
        />
      </div>
    );
  }

  return (
    <PageContainer>
      <PageIntro
        actions={
          <Button
            variant="outline"
            size="sm"
            disabled={items.length === 0}
            onClick={() => downloadCsv(`predictions-page-${page}.csv`, predictionsToCsv(items))}
          >
            <Download />
            Export CSV
          </Button>
        }
      >
        Every stored prediction, newest first. Select a row to see its full details.
      </PageIntro>

      <FilterBar isRefreshing={isFetching && !isPending} />

      <Card className="gap-0 py-0">
        {content}
        {data && data.total > 0 && (
          <nav
            aria-label="Pagination"
            className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3"
          >
            <p className="text-sm text-muted-foreground" aria-live="polite">
              {items.length > 0 ? (
                <>
                  Showing{" "}
                  <span className="font-medium text-foreground">
                    {formatNumber(first)}–{formatNumber(last)}
                  </span>{" "}
                  of <span className="font-medium text-foreground">{formatNumber(data.total)}</span>
                </>
              ) : (
                `${formatNumber(data.total)} predictions`
              )}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground tabular-nums">
                Page {formatNumber(page)} of {formatNumber(Math.max(data.pages, 1))}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1 || isPlaceholderData}
              >
                <ChevronLeft />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => goToPage(page + 1)}
                disabled={page >= data.pages || isPlaceholderData}
              >
                Next
                <ChevronRight />
              </Button>
            </div>
          </nav>
        )}
      </Card>

      <PredictionSheet
        id={selectedId}
        fromList={items.find((item) => item.id === selectedId)}
        onClose={() => updateSearchParams({ prediction: null })}
      />
    </PageContainer>
  );
}

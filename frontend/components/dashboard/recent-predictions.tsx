"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Inbox } from "lucide-react";
import Link from "next/link";
import { RelativeTime } from "@/components/common/relative-time";
import { TableCard } from "@/components/common/table-card";
import { ErrorState } from "@/components/feedback/error-state";
import { TableSkeleton } from "@/components/feedback/table-skeleton";
import { SentimentBadge } from "@/components/sentiment/sentiment-badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { filtersToQueryString, type Filters } from "@/lib/filters";
import { formatPercent } from "@/lib/format";
import { predictionsQuery } from "@/lib/queries";

const RECENT_COUNT = 8;

export function RecentPredictions({ filters }: { filters: Filters }) {
  const { data, error, isPending, isFetching, refetch } = useQuery(
    predictionsQuery(filters, 1, RECENT_COUNT, { live: true }),
  );
  const filterQuery = filtersToQueryString(filters);
  const withFilters = (path: string) => (filterQuery ? `${path}&${filterQuery}` : path);

  let content: React.ReactNode;
  if (isPending) {
    content = <TableSkeleton rows={RECENT_COUNT} />;
  } else if (error && !data) {
    content = (
      <ErrorState
        error={error}
        onRetry={() => refetch()}
        retrying={isFetching}
        className="m-4 w-auto"
      />
    );
  } else if (data.items.length === 0) {
    content = (
      <p className="flex items-center gap-2 px-4 py-6 text-sm text-muted-foreground">
        <Inbox className="size-4" aria-hidden />
        Nothing here yet.
      </p>
    );
  } else {
    content = (
      <Table>
        <TableHeader>
          <TableRow>
            {/* The time column is dropped on phones to leave room for the post. */}
            <TableHead className="hidden w-28 sm:table-cell">Time</TableHead>
            <TableHead className="pl-4 sm:pl-2">Post</TableHead>
            <TableHead>Sentiment</TableHead>
            <TableHead className="text-right">Confidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.items.map((item) => (
            <TableRow key={item.id}>
              <TableCell className="hidden text-xs text-muted-foreground sm:table-cell">
                <RelativeTime iso={item.created_at} />
              </TableCell>
              <TableCell className="w-full max-w-0 pl-4 sm:pl-2">
                <Link
                  href={withFilters(`/history?prediction=${encodeURIComponent(item.id)}`)}
                  title={item.text}
                  className="block truncate rounded-sm outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  {item.text}
                </Link>
              </TableCell>
              <TableCell>
                <SentimentBadge sentiment={item.sentiment} size="sm" />
              </TableCell>
              <TableCell className="text-right font-mono text-xs tabular-nums">
                {formatPercent(item.confidence)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    );
  }

  return (
    <TableCard
      title="Recent predictions"
      description={`The latest ${RECENT_COUNT} matching your filters.`}
      className="h-full"
      action={
        <Button asChild variant="ghost" size="sm">
          <Link href={filterQuery ? `/history?${filterQuery}` : "/history"}>
            View all in History
            <ArrowRight />
          </Link>
        </Button>
      }
    >
      {content}
    </TableCard>
  );
}

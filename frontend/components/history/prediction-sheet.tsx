"use client";

import { useQuery } from "@tanstack/react-query";
import { TriangleAlert } from "lucide-react";
import { useState } from "react";
import { CopyButton } from "@/components/common/copy-button";
import { ErrorState } from "@/components/feedback/error-state";
import { CacheBadge } from "@/components/sentiment/cache-badge";
import { HighlightedText } from "@/components/sentiment/highlighted-text";
import { ProbabilityBars } from "@/components/sentiment/probability-bars";
import { SentimentBadge } from "@/components/sentiment/sentiment-badge";
import { TopWordChips } from "@/components/sentiment/top-word-chips";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useNow } from "@/hooks/use-now";
import { formatDateTime, formatMs, formatPercent, formatRelativeTime } from "@/lib/format";
import { predictionQuery } from "@/lib/queries";
import type { PredictionRecord } from "@/lib/types";

/**
 * Full details for one prediction, opened from a History row (or a shared
 * ?prediction=<id> link). Rows already carry the full record, so it shows instantly;
 * the request only matters for links to a prediction that isn't on the current page.
 */
export function PredictionSheet({
  id,
  fromList,
  onClose,
}: {
  id: string | null;
  fromList?: PredictionRecord;
  onClose: () => void;
}) {
  // Keep showing the last prediction while the sheet animates closed.
  const [shownId, setShownId] = useState(id);
  if (id && id !== shownId) setShownId(id);

  return (
    <Sheet open={Boolean(id)} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full gap-0 data-[side=right]:sm:max-w-lg">
        <SheetHeader className="border-b">
          <SheetTitle>Prediction details</SheetTitle>
          <SheetDescription>Everything stored for this prediction.</SheetDescription>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto">
          {shownId && (
            <Details id={shownId} fromList={fromList?.id === shownId ? fromList : undefined} />
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Details({ id, fromList }: { id: string; fromList?: PredictionRecord }) {
  const { data, error, isPending, isFetching, refetch } = useQuery({
    ...predictionQuery(id),
    initialData: fromList,
  });

  if (isPending) {
    return (
      <div className="grid gap-4 p-4" aria-busy aria-label="Loading prediction">
        <Skeleton className="h-9 w-40 rounded-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (error && !data) {
    return (
      <ErrorState
        error={error}
        onRetry={() => refetch()}
        retrying={isFetching}
        className="m-4 w-auto"
      />
    );
  }

  return <DetailsBody record={data} />;
}

function DetailsBody({ record }: { record: PredictionRecord }) {
  const now = useNow();
  const rows: { label: string; value: React.ReactNode; copy?: string }[] = [
    {
      label: "Prediction ID",
      value: <code className="font-mono text-xs">{record.id}</code>,
      copy: record.id,
    },
    {
      label: "Created",
      value: `${formatDateTime(record.created_at)} (${formatRelativeTime(record.created_at, now)})`,
    },
    {
      label: "Model version",
      value: <code className="font-mono text-xs break-all">{record.model_version}</code>,
      copy: record.model_version,
    },
    { label: "Cache", value: <CacheBadge status={record.cache_status} compact /> },
    { label: "Latency", value: formatMs(record.latency_ms) },
    { label: "Source", value: record.source === "batch" ? "Batch upload" : "Single post" },
  ];
  if (record.batch_id) {
    rows.push({
      label: "Batch ID",
      value: <code className="font-mono text-xs">{record.batch_id}</code>,
      copy: record.batch_id,
    });
  }

  return (
    <div className="grid gap-6 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <SentimentBadge sentiment={record.sentiment} size="lg" />
        <div className="grid">
          <span className="text-lg font-semibold">{formatPercent(record.confidence)}</span>
          <span className="text-xs text-muted-foreground">estimated confidence</span>
        </div>
        {record.is_low_confidence && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-warning/10 px-2 py-1 text-xs font-medium text-warning-ink ring-1 ring-warning/30 ring-inset">
            <TriangleAlert className="size-3.5" aria-hidden />
            Low confidence
          </span>
        )}
      </div>

      <section className="grid gap-2">
        <h3 className="text-xs font-medium text-muted-foreground">Post</h3>
        <div className="rounded-lg bg-muted/40 p-3 ring-1 ring-foreground/5">
          <HighlightedText
            text={record.text}
            words={record.top_words}
            sentiment={record.sentiment}
          />
        </div>
      </section>

      <section className="grid gap-3">
        <h3 className="text-xs font-medium text-muted-foreground">Class probabilities</h3>
        <ProbabilityBars probabilities={record.probabilities} predicted={record.sentiment} />
      </section>

      {record.top_words.length > 0 && (
        <section className="grid gap-2">
          <h3 className="text-xs font-medium text-muted-foreground">Most influential words</h3>
          <TopWordChips words={record.top_words} sentiment={record.sentiment} />
        </section>
      )}

      <section className="grid gap-2">
        <h3 className="text-xs font-medium text-muted-foreground">Details</h3>
        <dl className="divide-y rounded-lg ring-1 ring-border">
          {rows.map((row) => (
            <div
              key={row.label}
              className="grid grid-cols-[7.5rem_1fr_auto] items-center gap-3 px-3 py-2 text-sm"
            >
              <dt className="text-muted-foreground">{row.label}</dt>
              <dd className="min-w-0">{row.value}</dd>
              <div className="w-6">
                {row.copy && <CopyButton value={row.copy} label={`Copy ${row.label}`} />}
              </div>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}

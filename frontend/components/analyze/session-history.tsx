"use client";

import { RelativeTime } from "@/components/common/relative-time";
import { CacheBadge } from "@/components/sentiment/cache-badge";
import { SentimentBadge } from "@/components/sentiment/sentiment-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatPercent } from "@/lib/format";
import type { PredictResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

/** The last few results from this visit (kept in memory only), most recent first. */
export function SessionHistory({
  items,
  activeId,
  onSelect,
}: {
  items: PredictResponse[];
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>This session</CardTitle>
        <CardDescription>
          {items.length
            ? "Select a result to view it again."
            : "Results you analyze will show up here."}
        </CardDescription>
      </CardHeader>
      {items.length > 0 && (
        <CardContent className="px-1.5">
          <ul className="grid gap-0.5">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect(item.id)}
                  aria-current={item.id === activeId ? "true" : undefined}
                  className={cn(
                    "grid w-full gap-1.5 rounded-lg px-2 py-2 text-left transition-colors outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50",
                    item.id === activeId && "bg-muted",
                  )}
                >
                  <span className="line-clamp-2 text-sm">{item.text}</span>
                  <span className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                    <SentimentBadge sentiment={item.sentiment} size="sm" />
                    <span className="font-mono tabular-nums">{formatPercent(item.confidence)}</span>
                    <CacheBadge status={item.cache_status} compact />
                    <RelativeTime iso={item.created_at} className="ml-auto" />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </CardContent>
      )}
    </Card>
  );
}

"use client";

import { RelativeTime } from "@/components/common/relative-time";
import { CacheBadge } from "@/components/sentiment/cache-badge";
import { SentimentBadge } from "@/components/sentiment/sentiment-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatPercent, shortVersion } from "@/lib/format";
import type { PredictionRecord } from "@/lib/types";

export function PredictionsTable({
  items,
  selectedId,
  onSelect,
}: {
  items: PredictionRecord[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-32">Time</TableHead>
          <TableHead>Post</TableHead>
          <TableHead>Sentiment</TableHead>
          <TableHead className="text-right">Confidence</TableHead>
          <TableHead>Cache</TableHead>
          <TableHead>Source</TableHead>
          <TableHead>Model</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          // The whole row opens the details; the button in the Post cell makes that
          // reachable by keyboard (Enter on it bubbles a click up to the row).
          <TableRow
            key={item.id}
            onClick={() => onSelect(item.id)}
            data-state={item.id === selectedId ? "selected" : undefined}
            className="cursor-pointer"
          >
            <TableCell className="text-xs text-muted-foreground">
              <RelativeTime iso={item.created_at} />
            </TableCell>
            <TableCell className="w-full max-w-0 min-w-48">
              <button
                type="button"
                title={item.text}
                className="block w-full truncate rounded-sm text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <span className="sr-only">View details: </span>
                {item.text}
              </button>
            </TableCell>
            <TableCell>
              <SentimentBadge sentiment={item.sentiment} size="sm" />
            </TableCell>
            <TableCell className="text-right font-mono text-xs tabular-nums">
              {formatPercent(item.confidence)}
            </TableCell>
            <TableCell>
              <CacheBadge status={item.cache_status} compact />
            </TableCell>
            <TableCell className="text-xs text-muted-foreground capitalize">
              {item.source}
            </TableCell>
            <TableCell>
              <code className="font-mono text-xs text-muted-foreground" title={item.model_version}>
                {shortVersion(item.model_version)}
              </code>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

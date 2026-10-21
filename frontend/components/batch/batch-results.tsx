"use client";

import { CircleAlert, CircleCheck, Download, Layers, RotateCcw, Zap } from "lucide-react";
import { useState } from "react";
import { SentimentDonut } from "@/components/charts/sentiment-donut";
import { CopyButton } from "@/components/common/copy-button";
import { StatCard } from "@/components/common/stat-card";
import { TableCard } from "@/components/common/table-card";
import { CacheBadge } from "@/components/sentiment/cache-badge";
import { SentimentBadge } from "@/components/sentiment/sentiment-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { batchResultsToCsv, downloadCsv } from "@/lib/csv";
import { formatCount, formatNumber, formatPercent, shortVersion } from "@/lib/format";
import type { BatchResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

export function BatchResults({ result, onReset }: { result: BatchResponse; onReset: () => void }) {
  const [showFailedOnly, setShowFailedOnly] = useState(false);
  const rows = showFailedOnly ? result.results.filter((row) => row.error) : result.results;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-1.5 text-sm text-muted-foreground">
          Batch <code className="truncate font-mono text-foreground">{result.batch_id}</code>
          <CopyButton value={result.batch_id} label="Copy batch ID" />
          <span aria-hidden>·</span> model
          <code className="font-mono" title={result.model_version}>
            {shortVersion(result.model_version)}
          </code>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onReset}>
            <RotateCcw />
            Analyze another file
          </Button>
          <Button
            size="sm"
            onClick={() =>
              downloadCsv(`batch-${result.batch_id}.csv`, batchResultsToCsv(result.results))
            }
          >
            <Download />
            Download results CSV
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          icon={Layers}
          label="Rows"
          value={formatNumber(result.total_rows)}
          sub="in the uploaded file"
        />
        <StatCard
          icon={CircleCheck}
          label="Succeeded"
          value={formatNumber(result.succeeded)}
          sub={`${formatPercent(result.total_rows ? result.succeeded / result.total_rows : null)} of rows`}
        />
        <StatCard
          icon={CircleAlert}
          label="Failed"
          value={formatNumber(result.failed)}
          sub={result.failed ? "highlighted in the table" : "no errors"}
          valueClassName={result.failed ? "text-destructive" : undefined}
        />
        <StatCard
          icon={Zap}
          label="Cache hits"
          value={formatNumber(result.cache.hit)}
          sub={`${formatCount(result.cache.miss, "miss", "misses")} · ${formatNumber(result.cache.bypass)} bypassed`}
        />
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Sentiment distribution</CardTitle>
            <CardDescription>
              Across the {formatCount(result.succeeded, "analyzed row")}.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SentimentDonut counts={result.summary} />
          </CardContent>
        </Card>

        <TableCard
          title="Results"
          description="One row per post, in file order."
          className="min-w-0 lg:col-span-3"
          action={
            result.failed > 0 && (
              <ToggleGroup
                type="single"
                variant="outline"
                size="sm"
                spacing={0}
                value={showFailedOnly ? "failed" : "all"}
                onValueChange={(value) => value && setShowFailedOnly(value === "failed")}
                aria-label="Rows to show"
              >
                <ToggleGroupItem value="all">All</ToggleGroupItem>
                <ToggleGroupItem value="failed">
                  Failed ({formatNumber(result.failed)})
                </ToggleGroupItem>
              </ToggleGroup>
            )
          }
        >
          <div className="max-h-[32rem] overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">Row</TableHead>
                  <TableHead>Post</TableHead>
                  <TableHead>Sentiment</TableHead>
                  <TableHead className="text-right">Confidence</TableHead>
                  <TableHead>Cache</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow
                    key={row.row}
                    className={cn(row.error && "bg-destructive/5 hover:bg-destructive/10")}
                  >
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {row.row}
                    </TableCell>
                    <TableCell className="w-full max-w-0 min-w-40 truncate" title={row.text}>
                      {row.text || <span className="text-muted-foreground italic">empty</span>}
                    </TableCell>
                    {row.error || !row.sentiment ? (
                      <TableCell colSpan={3}>
                        <span className="flex items-center gap-1.5 text-xs font-medium text-destructive">
                          <CircleAlert className="size-3.5 shrink-0" aria-hidden />
                          {row.error ?? "Not analyzed"}
                        </span>
                      </TableCell>
                    ) : (
                      <>
                        <TableCell>
                          <SentimentBadge sentiment={row.sentiment} size="sm" />
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs tabular-nums">
                          {formatPercent(row.confidence)}
                        </TableCell>
                        <TableCell>
                          {row.cache_status && <CacheBadge status={row.cache_status} compact />}
                        </TableCell>
                      </>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TableCard>
      </div>
    </div>
  );
}

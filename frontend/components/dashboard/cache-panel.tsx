"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleX, Cpu, RotateCw, Zap, ZapOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { describeError } from "@/lib/errors";
import { formatDuration, formatNumber, formatPercent } from "@/lib/format";
import { cacheStatsQuery } from "@/lib/queries";
import type { AnalyticsSummary, CacheStats } from "@/lib/types";

const PARTS = [
  { key: "hit", label: "Hit", icon: Zap, fill: "bg-cache-hit" },
  { key: "miss", label: "Miss", icon: Cpu, fill: "bg-cache-miss" },
  { key: "bypass", label: "Bypass", icon: ZapOff, fill: "bg-cache-bypass" },
] as const;

/** How the stored (filtered) predictions were served, plus the live Redis server stats. */
export function CachePanel({ stored }: { stored: AnalyticsSummary["cache"] }) {
  const total = stored.hit + stored.miss + stored.bypass;
  const summaryLabel = PARTS.map((p) => `${p.label} ${formatNumber(stored[p.key])}`).join(", ");

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Cache</CardTitle>
        <CardDescription>How stored predictions were served, and Redis right now.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <section className="grid gap-3">
          <h3 className="text-xs font-medium text-muted-foreground">Stored predictions</h3>
          <div role="img" aria-label={summaryLabel} className="flex h-2.5 gap-0.5">
            {total === 0 ? (
              <div className="flex-1 rounded-full bg-muted" />
            ) : (
              PARTS.filter((p) => stored[p.key] > 0).map((p) => (
                // flex-grow by count: proportional widths, with real 2px gaps between parts.
                <div
                  key={p.key}
                  className={`basis-0 rounded-full ${p.fill}`}
                  style={{ flexGrow: stored[p.key] }}
                />
              ))
            )}
          </div>
          <ul className="grid grid-cols-3 gap-2">
            {PARTS.map((p) => (
              <li key={p.key} className="grid gap-0.5">
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className={`size-2 rounded-[2px] ${p.fill}`} aria-hidden />
                  {p.label}
                </span>
                <span className="text-sm font-medium tabular-nums">
                  {formatNumber(stored[p.key])}
                  <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                    {formatPercent(total ? stored[p.key] / total : null, 0)}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="grid gap-3 border-t pt-5">
          <h3 className="text-xs font-medium text-muted-foreground">Redis · live</h3>
          <LiveRedis />
        </section>
      </CardContent>
    </Card>
  );
}

function LiveRedis() {
  const { data, error, isPending, isFetching, refetch } = useQuery(cacheStatsQuery());

  if (isPending) {
    return (
      <div className="grid grid-cols-2 gap-4" aria-hidden>
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-10" />
        ))}
      </div>
    );
  }

  if (error && !data) {
    const { title, requestId } = describeError(error);
    return (
      <div role="alert" className="flex items-center justify-between gap-3 text-sm">
        <div className="grid gap-0.5">
          <p className="font-medium">{title}</p>
          {requestId && (
            <p className="font-mono text-xs text-muted-foreground">Request ID {requestId}</p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RotateCw className={isFetching ? "animate-spin" : undefined} />
          Retry
        </Button>
      </div>
    );
  }

  if (!data.enabled) {
    return (
      <Notice
        icon={ZapOff}
        title="Caching is turned off"
        body="Every request is computed by the model."
      />
    );
  }
  if (!data.available) {
    return (
      <Notice
        icon={CircleX}
        title="Redis unavailable"
        body="Predictions still work: they're computed by the model and marked BYPASS until Redis is back."
      />
    );
  }
  return <RedisStats stats={data} />;
}

function RedisStats({ stats }: { stats: CacheStats }) {
  const items = [
    { label: "Keys", value: formatNumber(stats.keys) },
    { label: "TTL", value: formatDuration(stats.ttl_seconds) },
    { label: "Server hit rate", value: formatPercent(stats.hit_rate) },
    { label: "Memory", value: stats.used_memory_human ?? "—" },
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
      {items.map((item) => (
        <div key={item.label} className="grid gap-0.5">
          <dt className="text-xs text-muted-foreground">{item.label}</dt>
          <dd className="text-sm font-medium tabular-nums">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Notice({ icon: Icon, title, body }: { icon: typeof Zap; title: string; body: string }) {
  return (
    <div className="flex gap-2.5 rounded-lg bg-muted/50 p-3 text-sm">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
      <div className="grid gap-0.5">
        <p className="font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{body}</p>
      </div>
    </div>
  );
}

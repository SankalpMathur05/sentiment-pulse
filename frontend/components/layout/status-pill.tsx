"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleCheck, CircleMinus, CircleX, RotateCw } from "lucide-react";
import { RelativeTime } from "@/components/common/relative-time";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import { describeError } from "@/lib/errors";
import { formatDuration, formatMs, shortVersion } from "@/lib/format";
import { healthQuery } from "@/lib/queries";
import type { HealthReport, HealthStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const LEVELS: Record<HealthStatus, { label: string; dot: string }> = {
  ok: { label: "All systems operational", dot: "bg-status-ok ring-status-ok/20" },
  degraded: { label: "Degraded", dot: "bg-status-warn ring-status-warn/25" },
  down: { label: "Down", dot: "bg-status-down ring-status-down/25" },
};

export function StatusPillSkeleton() {
  return <Skeleton className="h-7 w-9 rounded-full sm:w-48" />;
}

/** Shown while the first health check is being retried, e.g. the hosted API is waking up. */
function WakingPill() {
  return (
    <span
      role="status"
      title="The free hosting plan pauses the API when it's idle. Starting it again takes up to a minute."
      className="inline-flex h-7 items-center gap-2 rounded-full border px-2.5 text-sm text-muted-foreground"
    >
      <span className="size-2 animate-pulse rounded-full bg-status-warn ring-3 ring-status-warn/25" />
      <span className="hidden sm:inline">Waking up the API…</span>
    </span>
  );
}

/** Live API health in the top bar; polls /health every 30 s. */
export function StatusPill() {
  const health = useQuery(healthQuery());
  if (health.isPending) {
    return health.failureCount > 0 ? <WakingPill /> : <StatusPillSkeleton />;
  }
  const { isFetching, refetch, dataUpdatedAt, errorUpdatedAt } = health;

  // If the latest check failed, older data can't be trusted: report the outage.
  const report = health.error ? undefined : health.data;
  const level: HealthStatus = report ? report.status : "down";
  const label = report ? LEVELS[level].label : "API unreachable";
  const checkedAt = new Date(Math.max(dataUpdatedAt, errorUpdatedAt)).toISOString();

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-2 rounded-full px-2.5 font-normal"
          aria-label={`System status: ${label}. Show details`}
        >
          <span className={cn("size-2 rounded-full ring-3", LEVELS[level].dot)} />
          <span className="hidden sm:inline">{label}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 gap-0 p-0">
        <div className="flex items-start justify-between gap-3 border-b p-3">
          <div className="grid gap-0.5">
            <p className="text-sm font-medium">{label}</p>
            <p className="text-xs text-muted-foreground">
              Checked <RelativeTime iso={checkedAt} /> · refreshes every 30 s
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => refetch()}
            disabled={isFetching}
            aria-label="Check again"
          >
            <RotateCw className={cn(isFetching && "animate-spin")} />
          </Button>
        </div>
        {report ? <HealthDetails report={report} /> : <UnreachableDetails error={health.error} />}
      </PopoverContent>
    </Popover>
  );
}

function HealthDetails({ report }: { report: HealthReport }) {
  const { model, database, redis } = report.checks;
  const rows = [
    {
      name: "Model",
      status: model.status,
      detail: model.version ? shortVersion(model.version) : "Not loaded",
      mono: Boolean(model.version),
    },
    {
      name: "Database",
      status: database.status,
      detail: database.error ?? formatMs(database.latency_ms),
      mono: false,
    },
    {
      name: "Redis cache",
      status: redis.status,
      detail:
        redis.status === "disabled" ? "Disabled" : (redis.error ?? formatMs(redis.latency_ms)),
      mono: false,
    },
  ];

  return (
    <>
      <ul className="grid gap-0.5 p-1.5">
        {rows.map((row) => (
          <li key={row.name} className="flex items-center gap-2.5 rounded-md px-1.5 py-1.5 text-sm">
            <CheckIcon status={row.status} />
            <span className="font-medium">{row.name}</span>
            <span
              title={row.detail}
              className={cn(
                "ml-auto max-w-40 truncate text-xs text-muted-foreground",
                row.mono && "font-mono",
              )}
            >
              {row.detail}
            </span>
          </li>
        ))}
      </ul>
      <p className="border-t px-3 py-2 text-xs text-muted-foreground">
        API <span className="font-mono">{report.version}</span> · {report.environment} · up{" "}
        {formatDuration(report.uptime_seconds)}
      </p>
    </>
  );
}

function CheckIcon({ status }: { status: string }) {
  if (status === "ok") return <CircleCheck className="size-4 text-status-ok" aria-label="OK" />;
  if (status === "disabled") {
    return <CircleMinus className="size-4 text-muted-foreground" aria-label="Disabled" />;
  }
  return <CircleX className="size-4 text-status-down" aria-label="Down" />;
}

function UnreachableDetails({ error }: { error: unknown }) {
  const { message, requestId } = describeError(error);
  return (
    <div className="grid gap-1 p-3 text-sm">
      <p className="text-muted-foreground">{message}</p>
      {requestId && (
        <p className="text-xs text-muted-foreground">
          Request ID <code className="font-mono">{requestId}</code>
        </p>
      )}
    </div>
  );
}

import { Cpu, Zap, ZapOff } from "lucide-react";
import { formatMs } from "@/lib/format";
import type { CacheStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const CACHE_STYLES = {
  hit: {
    icon: Zap,
    short: "HIT",
    hint: "Served from the Redis cache",
    className: "bg-cache-hit/10 text-violet-700 ring-cache-hit/25 dark:text-violet-300",
  },
  miss: {
    icon: Cpu,
    short: "MISS",
    hint: "Not cached yet, so the model computed it",
    className: "bg-muted text-muted-foreground ring-border",
  },
  bypass: {
    icon: ZapOff,
    short: "BYPASS",
    hint: "Cache unavailable, so the model computed it",
    className: "bg-warning/10 text-warning-ink ring-warning/30",
  },
} satisfies Record<CacheStatus, unknown>;

function describe(status: CacheStatus, latencyMs?: number): string {
  const latency = latencyMs == null ? null : formatMs(latencyMs);
  if (status === "hit")
    return ["Cache HIT", latency, "served from Redis"].filter(Boolean).join(" · ");
  if (status === "miss")
    return ["Cache MISS", "computed by model", latency].filter(Boolean).join(" · ");
  return "Cache unavailable · computed by model";
}

/**
 * Where a prediction came from. `compact` is for tables ("HIT"); the full form
 * spells it out ("Cache HIT · 2.1 ms · served from Redis").
 */
export function CacheBadge({
  status,
  latencyMs,
  compact = false,
  className,
}: {
  status: CacheStatus;
  latencyMs?: number;
  compact?: boolean;
  className?: string;
}) {
  const { icon: Icon, short, hint, className: tone } = CACHE_STYLES[status];
  return (
    <span
      title={compact ? hint : undefined}
      className={cn(
        "inline-flex w-fit shrink-0 items-center gap-1.5 rounded-full font-medium whitespace-nowrap ring-1 ring-inset",
        compact
          ? "h-5 px-1.5 text-[11px] tracking-wide [&_svg]:size-3"
          : "h-6 px-2 text-xs [&_svg]:size-3.5",
        tone,
        className,
      )}
    >
      <Icon />
      {compact ? short : describe(status, latencyMs)}
    </span>
  );
}

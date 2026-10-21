import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** A labelled headline number with a short supporting line, and an optional share meter. */
export function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  meter,
  badge,
  valueClassName,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  sub: string;
  /** A 0–1 share drawn as a thin bar, in the given fill colour class. */
  meter?: { value: number; className: string };
  /** Shown at the end of the label row. */
  badge?: React.ReactNode;
  valueClassName?: string;
}) {
  return (
    <Card size="sm" className="gap-1.5 px-3.5">
      <div className="flex min-h-5 items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Icon className="size-3.5" aria-hidden />
        {label}
        {badge && <span className="ml-auto">{badge}</span>}
      </div>
      <p className={cn("text-2xl font-semibold tracking-tight", valueClassName)}>{value}</p>
      <p className="truncate text-xs text-muted-foreground">{sub}</p>
      {meter && (
        <div className="mt-1 h-1 overflow-hidden rounded-full bg-muted" aria-hidden>
          <div
            className={cn("h-full rounded-full", meter.className)}
            style={{ width: `${meter.value * 100}%` }}
          />
        </div>
      )}
    </Card>
  );
}

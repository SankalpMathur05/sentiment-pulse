"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useNow } from "@/hooks/use-now";
import { formatDateTime, formatRelativeTime } from "@/lib/format";

/** "5 minutes ago", with the exact local time in a tooltip. */
export function RelativeTime({ iso, className }: { iso: string; className?: string }) {
  const now = useNow();
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <time dateTime={iso} className={className}>
          {formatRelativeTime(iso, now)}
        </time>
      </TooltipTrigger>
      <TooltipContent>{formatDateTime(iso)}</TooltipContent>
    </Tooltip>
  );
}

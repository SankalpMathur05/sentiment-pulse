"use client";

import { RotateCw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import { describeError } from "@/lib/errors";
import { cn } from "@/lib/utils";

/** What a data view shows when its request failed: what happened, the request id, and Retry. */
export function ErrorState({
  error,
  onRetry,
  retrying = false,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
}) {
  const { title, message, requestId } = describeError(error);
  return (
    <Empty role="alert" className={cn("border border-dashed border-destructive/30", className)}>
      <EmptyHeader>
        <EmptyMedia variant="icon" className="bg-destructive/10 text-destructive">
          <TriangleAlert />
        </EmptyMedia>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{message}</EmptyDescription>
      </EmptyHeader>
      {(onRetry || requestId) && (
        <EmptyContent>
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry} disabled={retrying}>
              {retrying ? <Spinner /> : <RotateCw />}
              Retry
            </Button>
          )}
          {requestId && (
            <p className="text-xs text-muted-foreground">
              Request ID <code className="font-mono select-all">{requestId}</code>
            </p>
          )}
        </EmptyContent>
      )}
    </Empty>
  );
}

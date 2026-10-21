"use client";

import { RotateCw, Sparkles, TriangleAlert } from "lucide-react";
import { InfoTooltip } from "@/components/common/info-tooltip";
import { RelativeTime } from "@/components/common/relative-time";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { CacheBadge } from "@/components/sentiment/cache-badge";
import { HighlightedText } from "@/components/sentiment/highlighted-text";
import { ProbabilityBars } from "@/components/sentiment/probability-bars";
import { SentimentBadge } from "@/components/sentiment/sentiment-badge";
import { TopWordChips } from "@/components/sentiment/top-word-chips";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { describeError } from "@/lib/errors";
import { formatPercent, shortVersion } from "@/lib/format";
import { SENTIMENT_STYLES } from "@/lib/sentiment";
import type { PredictResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

export function PredictionResult({
  result,
  isPending,
  error,
  onRetry,
  onAnalyzeAgain,
}: {
  result: PredictResponse | null;
  isPending: boolean;
  error: unknown;
  onRetry: () => void;
  onAnalyzeAgain: (text: string) => void;
}) {
  let announcement = "";
  if (isPending) announcement = "Analyzing…";
  else if (error) announcement = `Analysis failed. ${describeError(error).message}`;
  else if (result) {
    announcement = `Result: ${SENTIMENT_STYLES[result.sentiment].label}, ${formatPercent(result.confidence)} estimated confidence.`;
  }

  let content: React.ReactNode;
  if (error && !isPending) {
    content = <ErrorState error={error} onRetry={onRetry} />;
  } else if (result) {
    content = <ResultCard result={result} isPending={isPending} onAnalyzeAgain={onAnalyzeAgain} />;
  } else if (isPending) {
    content = <ResultSkeleton />;
  } else {
    content = (
      <EmptyState
        icon={Sparkles}
        title="Your result will appear here"
        description="Write or paste a post, or pick an example above, then press Analyze."
        className="py-12"
      />
    );
  }

  return (
    <section aria-label="Prediction result" aria-busy={isPending}>
      {/* Screen readers hear the outcome without having to find the card. */}
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
      {content}
    </section>
  );
}

function ResultCard({
  result,
  isPending,
  onAnalyzeAgain,
}: {
  result: PredictResponse;
  isPending: boolean;
  onAnalyzeAgain: (text: string) => void;
}) {
  const style = SENTIMENT_STYLES[result.sentiment];

  return (
    // Keep the previous result on screen (dimmed) while the next one loads.
    <Card className={cn("transition-opacity", isPending && "opacity-60")}>
      <CardHeader className="flex flex-wrap items-center justify-between gap-3 border-b">
        <SentimentBadge sentiment={result.sentiment} size="lg" />
        <CacheBadge status={result.cache_status} latencyMs={result.latency_ms} />
      </CardHeader>

      <CardContent className="grid gap-7">
        <div className="grid gap-2.5">
          <div className="flex items-end justify-between gap-4">
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              Estimated confidence
              <InfoTooltip label="About estimated confidence">
                The model&apos;s estimated probability — an estimate, not a guarantee.
              </InfoTooltip>
            </div>
            <p className="text-3xl font-semibold tracking-tight">
              {formatPercent(result.confidence)}
            </p>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
            <div
              className={cn("h-full rounded-full transition-[width] duration-500", style.fillClass)}
              style={{ width: `${result.confidence * 100}%` }}
            />
          </div>
        </div>

        {result.is_low_confidence && (
          <Alert className="border-warning/30 bg-warning/10 text-warning-ink">
            <TriangleAlert />
            <AlertTitle>Low confidence</AlertTitle>
            <AlertDescription className="text-warning-ink/90">
              Posts like this (sarcasm, mixed feelings) are hard for this model.
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-3">
          <h3 className="text-sm font-medium">Class probabilities</h3>
          <ProbabilityBars probabilities={result.probabilities} predicted={result.sentiment} />
        </div>

        <div className="grid gap-3">
          <div className="grid gap-1">
            <h3 className="text-sm font-medium">Why this label?</h3>
            <p className="text-xs text-muted-foreground">
              The words that pushed the model towards{" "}
              <span className="font-medium">{style.label}</span>. A stronger tint means more
              influence.
            </p>
          </div>
          <div className="rounded-lg bg-muted/40 p-4 ring-1 ring-foreground/5">
            <HighlightedText
              text={result.text}
              words={result.top_words}
              sentiment={result.sentiment}
            />
          </div>
          {result.top_words.length > 0 ? (
            <TopWordChips words={result.top_words} sentiment={result.sentiment} />
          ) : (
            <p className="text-sm text-muted-foreground">
              No single word stood out, so the label comes from the model&apos;s overall leaning for
              short or unfamiliar text.
            </p>
          )}
        </div>
      </CardContent>

      <CardFooter className="flex-wrap justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          Model{" "}
          <code className="font-mono text-foreground/80" title={result.model_version}>
            {shortVersion(result.model_version)}
          </code>{" "}
          · <RelativeTime iso={result.created_at} />
        </p>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onAnalyzeAgain(result.text)}
          disabled={isPending}
        >
          {isPending ? <Spinner /> : <RotateCw />}
          Analyze again
        </Button>
      </CardFooter>
    </Card>
  );
}

function ResultSkeleton() {
  return (
    <Card aria-hidden>
      <CardHeader className="flex items-center justify-between border-b">
        <Skeleton className="h-9 w-32 rounded-full" />
        <Skeleton className="h-6 w-56 rounded-full" />
      </CardHeader>
      <CardContent className="grid gap-7">
        <div className="grid gap-3">
          <div className="flex items-end justify-between">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-8 w-20" />
          </div>
          <Skeleton className="h-2 w-full rounded-full" />
        </div>
        <div className="grid gap-3">
          <Skeleton className="h-4 w-32" />
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-3 w-full" />
          ))}
        </div>
        <Skeleton className="h-20 w-full" />
      </CardContent>
    </Card>
  );
}

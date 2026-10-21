import { formatPercent } from "@/lib/format";
import { SENTIMENT_STYLES, SENTIMENTS } from "@/lib/sentiment";
import type { Sentiment, SentimentProbabilities } from "@/lib/types";
import { cn } from "@/lib/utils";

/** One bar per class; the predicted class is emphasised. */
export function ProbabilityBars({
  probabilities,
  predicted,
}: {
  probabilities: SentimentProbabilities;
  predicted?: Sentiment;
}) {
  return (
    <ul className="grid gap-2.5">
      {SENTIMENTS.map((sentiment) => {
        const { label, icon: Icon, fillClass, textClass } = SENTIMENT_STYLES[sentiment];
        const value = probabilities[sentiment] ?? 0;
        const isPredicted = sentiment === predicted;
        return (
          <li
            key={sentiment}
            className="grid grid-cols-[6.5rem_1fr_3.5rem] items-center gap-3 text-sm"
          >
            <span
              className={cn(
                "flex items-center gap-1.5",
                isPredicted ? cn("font-medium", textClass) : "text-muted-foreground",
              )}
            >
              <Icon className="size-3.5" />
              {label}
            </span>
            <span className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
              <span
                className={cn(
                  "block h-full rounded-full transition-[width] duration-500",
                  fillClass,
                )}
                style={{ width: `${Math.max(value * 100, value > 0 ? 1 : 0)}%` }}
              />
            </span>
            <span
              className={cn(
                "text-right font-mono text-xs tabular-nums",
                isPredicted ? "font-medium text-foreground" : "text-muted-foreground",
              )}
            >
              {formatPercent(value)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

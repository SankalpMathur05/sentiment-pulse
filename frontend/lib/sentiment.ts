import { Frown, Meh, Smile, type LucideIcon } from "lucide-react";
import type { Sentiment } from "./types";

// The single source of truth for how a sentiment looks. Colours come from the CSS
// variables in globals.css, so badges, bars and charts always agree in both themes.

interface SentimentStyle {
  label: string;
  icon: LucideIcon;
  /** CSS colour for chart marks (fills, strokes). */
  color: string;
  /** Tinted pill: badge background + readable text colour. */
  badgeClass: string;
  /** Solid fill for bars and swatches. */
  fillClass: string;
  /** Readable text colour on a neutral surface. */
  textClass: string;
}

/** Display order: neutral sits between the two poles, like a diverging scale. */
export const SENTIMENTS = [
  "positive",
  "neutral",
  "negative",
] as const satisfies readonly Sentiment[];

export const SENTIMENT_STYLES: Record<Sentiment, SentimentStyle> = {
  positive: {
    label: "Positive",
    icon: Smile,
    color: "var(--sentiment-positive)",
    badgeClass: "bg-sentiment-positive/10 text-sentiment-positive-ink ring-sentiment-positive/25",
    fillClass: "bg-sentiment-positive",
    textClass: "text-sentiment-positive-ink",
  },
  neutral: {
    label: "Neutral",
    icon: Meh,
    color: "var(--sentiment-neutral)",
    badgeClass: "bg-sentiment-neutral/12 text-sentiment-neutral-ink ring-sentiment-neutral/30",
    fillClass: "bg-sentiment-neutral",
    textClass: "text-sentiment-neutral-ink",
  },
  negative: {
    label: "Negative",
    icon: Frown,
    color: "var(--sentiment-negative)",
    badgeClass: "bg-sentiment-negative/10 text-sentiment-negative-ink ring-sentiment-negative/25",
    fillClass: "bg-sentiment-negative",
    textClass: "text-sentiment-negative-ink",
  },
};

export function isSentiment(value: unknown): value is Sentiment {
  return value === "positive" || value === "neutral" || value === "negative";
}

/** The analytics distribution as a lookup, with 0 for any class that is missing. */
export function countsBySentiment(
  distribution: { sentiment: Sentiment; count: number }[],
): Record<Sentiment, number> {
  const counts: Record<Sentiment, number> = { positive: 0, neutral: 0, negative: 0 };
  for (const share of distribution) counts[share.sentiment] = share.count;
  return counts;
}

/** Tint for a highlighted word: stronger weight, stronger background. */
export function weightTint(sentiment: Sentiment, weight: number, maxWeight: number): string {
  const strength = maxWeight > 0 ? Math.min(Math.abs(weight) / maxWeight, 1) : 0;
  const percent = Math.round(10 + strength * 25);
  return `color-mix(in oklch, ${SENTIMENT_STYLES[sentiment].color} ${percent}%, transparent)`;
}

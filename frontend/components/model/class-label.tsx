import { SentimentBadge } from "@/components/sentiment/sentiment-badge";
import { isSentiment, SENTIMENTS } from "@/lib/sentiment";

/** Sentiment labels in display order first, then anything else the model reports. */
export function orderedLabels(labels: string[]): string[] {
  const known = SENTIMENTS.filter((s) => labels.includes(s));
  return [...known, ...labels.filter((label) => !isSentiment(label))];
}

/** A class name from the model card, shown as a sentiment badge when it is one. */
export function ClassLabel({ label }: { label: string }) {
  return isSentiment(label) ? <SentimentBadge sentiment={label} size="sm" /> : <span>{label}</span>;
}

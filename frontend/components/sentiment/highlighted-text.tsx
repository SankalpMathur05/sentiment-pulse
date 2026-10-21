import { highlightSegments } from "@/lib/highlight";
import { weightTint } from "@/lib/sentiment";
import type { Sentiment, TopWord } from "@/lib/types";

/** The post with its most influential words marked; stronger words get a stronger tint. */
export function HighlightedText({
  text,
  words,
  sentiment,
}: {
  text: string;
  words: TopWord[];
  sentiment: Sentiment;
}) {
  const maxWeight = Math.max(0, ...words.map((w) => Math.abs(w.weight)));
  return (
    <p className="text-[15px] leading-7 break-words whitespace-pre-wrap">
      {highlightSegments(text, words).map((segment, i) =>
        segment.word ? (
          <mark
            key={i}
            title={`"${segment.word.display}" weight ${segment.word.weight.toFixed(2)}`}
            className="rounded-[4px] [box-decoration-break:clone] px-0.5 py-px text-foreground"
            style={{ backgroundColor: weightTint(sentiment, segment.word.weight, maxWeight) }}
          >
            {segment.text}
          </mark>
        ) : (
          <span key={i}>{segment.text}</span>
        ),
      )}
    </p>
  );
}

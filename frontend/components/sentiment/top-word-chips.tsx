import { weightTint } from "@/lib/sentiment";
import type { Sentiment, TopWord } from "@/lib/types";

/** Word chips with their weight, tinted like the highlights in the text. */
export function TopWordChips({ words, sentiment }: { words: TopWord[]; sentiment: Sentiment }) {
  const maxWeight = Math.max(0, ...words.map((w) => Math.abs(w.weight)));
  return (
    <ul className="flex flex-wrap gap-1.5">
      {words.map((word) => (
        <li
          key={word.token}
          title={`Model token: ${word.token}`}
          className="inline-flex h-7 items-center gap-2 rounded-md px-2 text-sm ring-1 ring-foreground/5 ring-inset"
          style={{ backgroundColor: weightTint(sentiment, word.weight, maxWeight) }}
        >
          <span className="font-medium">{word.display}</span>
          <span className="font-mono text-xs text-foreground/70 tabular-nums">
            {word.weight >= 0 ? "+" : ""}
            {word.weight.toFixed(2)}
          </span>
        </li>
      ))}
    </ul>
  );
}

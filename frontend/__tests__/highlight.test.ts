import { describe, expect, it } from "vitest";
import { highlightSegments } from "@/lib/highlight";
import type { TopWord } from "@/lib/types";

const word = (token: string, weight: number, display = token): TopWord => ({
  token,
  display,
  weight,
});

const highlighted = (text: string, words: TopWord[]) =>
  highlightSegments(text, words)
    .filter((segment) => segment.word)
    .map((segment) => segment.text);

describe("highlightSegments", () => {
  it("marks matching words case-insensitively", () => {
    expect(highlighted("GREAT flight, really Great crew", [word("great", 0.8)])).toEqual([
      "GREAT",
      "Great",
    ]);
  });

  it("only matches whole words", () => {
    expect(highlighted("The greatest delay", [word("great", 0.8)])).toEqual([]);
  });

  it("keeps the original text intact", () => {
    const text = "Best flight ever, thank you!";
    const joined = highlightSegments(text, [word("best", 0.5), word("thank", 0.4)])
      .map((segment) => segment.text)
      .join("");
    expect(joined).toBe(text);
  });

  it("prefers a bigram over the single words inside it", () => {
    const segments = highlightSegments("The crew was not unhelpful at all", [
      word("not", 0.3),
      word("not unhelpful", 0.6),
    ]);
    expect(segments.filter((s) => s.word).map((s) => [s.text, s.word?.token])).toEqual([
      ["not unhelpful", "not unhelpful"],
    ]);
  });

  it("matches emoji, punctuation tokens and @mention placeholders", () => {
    const words = [
      word(":face_with_rolling_eyes:", 0.7, "🙄"),
      word("!", 0.2),
      word("<user>", 0.1, "@mention"),
    ];
    expect(highlighted("Thanks @united! 🙄", words)).toEqual(["@united", "!", "🙄"]);
  });
});

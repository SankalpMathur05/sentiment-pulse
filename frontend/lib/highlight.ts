import type { TopWord } from "./types";

export interface TextSegment {
  text: string;
  /** The top word this piece of text matched, or null for plain text. */
  word: TopWord | null;
}

// The model's text cleaner swaps these for placeholder tokens, so they never appear
// literally in the post. Match what they stood for instead.
const PLACEHOLDER_PATTERNS: Record<string, string> = {
  "<user>": String.raw`@\w+`,
  "<url>": String.raw`(?:https?:\/\/|www\.)\S+`,
};

const WORD_CHAR = /[\p{L}\p{N}_]/u;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Regex for one top word: each part of a unigram/bigram, case-insensitive. */
function patternFor(word: TopWord): RegExp | null {
  const tokenParts = word.token.split(" ");
  const displayParts = word.display.split(" ");

  const parts = tokenParts.map((tokenPart, i) => {
    const placeholder = PLACEHOLDER_PATTERNS[tokenPart];
    if (placeholder) return placeholder;
    const display = displayParts[i] ?? tokenPart;
    // The cleaner straightens curly apostrophes, so "don't" should match "don’t" too.
    return escapeRegExp(display).replace(/'/g, "['’]");
  });
  if (parts.length === 0 || parts.some((part) => part === "")) return null;

  // Bigram parts may be separated by spaces or punctuation the cleaner dropped.
  let source = parts.join(String.raw`[^\p{L}\p{N}]*`);

  // Whole words only ("great" must not light up inside "greatest"), but only on sides
  // that are word characters, so "!" and emoji still match next to letters.
  const first = word.display[0] ?? "";
  const last = word.display.at(-1) ?? "";
  if (WORD_CHAR.test(first)) source = String.raw`(?<![\p{L}\p{N}_])` + source;
  if (WORD_CHAR.test(last)) source += String.raw`(?![\p{L}\p{N}_])`;

  return new RegExp(source, "giu");
}

interface Match {
  start: number;
  end: number;
  word: TopWord;
}

/**
 * Split a post into plain and highlighted segments for the given top words.
 * When matches overlap, the longer one (a bigram) wins, then the heavier word.
 */
export function highlightSegments(text: string, words: TopWord[]): TextSegment[] {
  const matches: Match[] = [];
  for (const word of words) {
    const pattern = patternFor(word);
    if (!pattern) continue;
    for (const match of text.matchAll(pattern)) {
      if (match[0].length === 0) continue;
      matches.push({ start: match.index, end: match.index + match[0].length, word });
    }
  }

  const chosen: Match[] = [];
  const byPriority = [...matches].sort(
    (a, b) => b.end - b.start - (a.end - a.start) || b.word.weight - a.word.weight,
  );
  for (const match of byPriority) {
    const overlaps = chosen.some((c) => match.start < c.end && match.end > c.start);
    if (!overlaps) chosen.push(match);
  }
  chosen.sort((a, b) => a.start - b.start);

  const segments: TextSegment[] = [];
  let cursor = 0;
  for (const match of chosen) {
    if (match.start > cursor) segments.push({ text: text.slice(cursor, match.start), word: null });
    segments.push({ text: text.slice(match.start, match.end), word: match.word });
    cursor = match.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), word: null });
  return segments;
}

import Papa from "papaparse";
import { formatBytes, formatNumber } from "./format";
import type { BatchResultRow, PredictionRecord } from "./types";

export const BATCH_LIMITS = { maxRows: 500, maxBytes: 1024 * 1024 } as const;

const PREVIEW_ROWS = 5;

const SAMPLE_POSTS = [
  "Best flight ever, thank you for the upgrade! 😍",
  "Oh great, another 3 hour delay. Thanks @united 🙄",
  "The crew was not unhelpful at all",
  "Loved the new seats but the food was awful",
  "What time does boarding start for flight 202?",
  "Lost my bag AGAIN. Third time this year. Never flying with you again.",
  "Smooth check-in and we landed 20 minutes early :)",
  "Is there wifi on the 7am flight to Boston?",
  "Customer service hung up on me twice. Unbelievable.",
  "Thanks for the quick rebooking, really appreciate it!",
];

/** A small, varied CSV that matches the upload format. */
export function sampleCsv(): string {
  return Papa.unparse({ fields: ["text"], data: SAMPLE_POSTS.map((text) => [text]) });
}

export function downloadCsv(filename: string, csv: string): void {
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function predictionsToCsv(records: PredictionRecord[]): string {
  return Papa.unparse(
    records.map((r) => ({
      created_at: r.created_at,
      id: r.id,
      text: r.text,
      sentiment: r.sentiment,
      confidence: r.confidence,
      p_negative: r.probabilities.negative,
      p_neutral: r.probabilities.neutral,
      p_positive: r.probabilities.positive,
      low_confidence: r.is_low_confidence,
      top_words: r.top_words.map((w) => `${w.display} (${w.weight})`).join("; "),
      cache_status: r.cache_status,
      source: r.source,
      batch_id: r.batch_id ?? "",
      model_version: r.model_version,
      latency_ms: r.latency_ms,
    })),
  );
}

export function batchResultsToCsv(rows: BatchResultRow[]): string {
  return Papa.unparse(
    rows.map((r) => ({
      row: r.row,
      text: r.text,
      sentiment: r.sentiment ?? "",
      confidence: r.confidence ?? "",
      cache_status: r.cache_status ?? "",
      id: r.id ?? "",
      error: r.error ?? "",
    })),
  );
}

export interface CsvInspection {
  rowCount: number;
  /** First few values of the text column, for the preview table. */
  preview: string[];
  emptyTextRows: number;
  /** Blocks the upload: the API would reject this file. */
  error: string | null;
}

function rejected(error: string, rowCount = 0): CsvInspection {
  return { rowCount, preview: [], emptyTextRows: 0, error };
}

/** Check a CSV in the browser with the same rules the API applies, before uploading. */
export async function inspectCsv(file: File): Promise<CsvInspection> {
  if (!file.name.toLowerCase().endsWith(".csv")) return rejected("Choose a .csv file.");
  if (file.size > BATCH_LIMITS.maxBytes) {
    return rejected(
      `This file is ${formatBytes(file.size)}; the limit is ${formatBytes(BATCH_LIMITS.maxBytes)}.`,
    );
  }

  let content: string;
  try {
    content = await file.text();
  } catch {
    return rejected("This file couldn't be read.");
  }

  const parsed = Papa.parse<Record<string, string | undefined>>(content, {
    header: true,
    skipEmptyLines: true,
  });
  const columns = parsed.meta.fields ?? [];
  const textColumn = columns.find((column) => column.trim().toLowerCase() === "text");
  const rows = parsed.data;

  if (!textColumn) {
    const found = columns.length ? ` Columns found: ${columns.join(", ")}.` : "";
    return rejected(`No "text" column found.${found}`);
  }
  if (rows.length === 0) return rejected("This file has a header but no rows.");
  if (rows.length > BATCH_LIMITS.maxRows) {
    return rejected(
      `This file has ${formatNumber(rows.length)} rows; the limit is ${BATCH_LIMITS.maxRows}. Split it into smaller files.`,
      rows.length,
    );
  }

  const texts = rows.map((row) => (row[textColumn] ?? "").trim());
  return {
    rowCount: rows.length,
    preview: texts.slice(0, PREVIEW_ROWS),
    emptyTextRows: texts.filter((text) => text === "").length,
    error: null,
  };
}

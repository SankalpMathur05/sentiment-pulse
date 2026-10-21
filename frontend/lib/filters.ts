import { isSentiment } from "./sentiment";
import type { AnalyticsParams, Sentiment } from "./types";

// Dashboard/History filters live in the URL so a filtered view can be shared.
// Dates are kept as the browser's local "YYYY-MM-DDTHH:mm" (what <input
// type="datetime-local"> uses) and only converted to UTC ISO strings for the API.

export type QuickRange = "24h" | "7d" | "30d";

export const QUICK_RANGES: { value: QuickRange; label: string; hours: number }[] = [
  { value: "24h", label: "24h", hours: 24 },
  { value: "7d", label: "7d", hours: 24 * 7 },
  { value: "30d", label: "30d", hours: 24 * 30 },
];

export interface Filters {
  sentiment: Sentiment | null;
  /** A rolling window ending now; mutually exclusive with from/to. */
  range: QuickRange | null;
  from: string | null;
  to: string | null;
}

export const FILTER_PARAM_KEYS = ["sentiment", "range", "from", "to"] as const;

export const EMPTY_FILTERS: Filters = { sentiment: null, range: null, from: null, to: null };

export function parseFilters(params: { get(name: string): string | null }): Filters {
  const sentiment = params.get("sentiment");
  const range = params.get("range");
  return {
    sentiment: isSentiment(sentiment) ? sentiment : null,
    range: QUICK_RANGES.some((r) => r.value === range) ? (range as QuickRange) : null,
    from: params.get("from") || null,
    to: params.get("to") || null,
  };
}

/** The filters as URL search params (missing values are omitted). */
export function filtersToParams(
  filters: Filters,
): Record<(typeof FILTER_PARAM_KEYS)[number], string | null> {
  return {
    sentiment: filters.sentiment,
    range: filters.range,
    from: filters.range ? null : filters.from,
    to: filters.range ? null : filters.to,
  };
}

export function filtersToQueryString(filters: Filters): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(filtersToParams(filters))) {
    if (value) search.set(key, value);
  }
  return search.toString();
}

export function hasActiveFilters(filters: Filters): boolean {
  return Boolean(filters.sentiment || filters.range || filters.from || filters.to);
}

function localToIso(value: string | null): string | undefined {
  if (!value) return undefined;
  const date = new Date(value); // a date-time without an offset is parsed as local time
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}

/** API query params. Call this when fetching, so a quick range always ends "now". */
export function toApiParams(filters: Filters, now: number = Date.now()): AnalyticsParams {
  const params: AnalyticsParams = {};
  if (filters.sentiment) params.sentiment = filters.sentiment;

  const quickRange = QUICK_RANGES.find((r) => r.value === filters.range);
  if (quickRange) {
    params.date_from = new Date(now - quickRange.hours * 3_600_000).toISOString();
  } else {
    params.date_from = localToIso(filters.from);
    params.date_to = localToIso(filters.to);
  }
  return params;
}

/** Inline validation message for the date inputs, or null when they make sense. */
export function dateRangeError(filters: Filters): string | null {
  const from = localToIso(filters.from);
  const to = localToIso(filters.to);
  return from && to && from > to ? "The start date must be before the end date." : null;
}

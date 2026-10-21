// Number, time and size formatting. Every helper returns "—" for missing values so
// views never have to special-case null.

const EMPTY = "—";

const numberFormat = new Intl.NumberFormat("en-US");
const relativeFormat = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const dateTimeFormat = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeStyle: "medium",
});
const dateFormat = new Intl.DateTimeFormat("en", { dateStyle: "medium" });

/** 1234 → "1,234" */
export function formatNumber(value: number | null | undefined): string {
  return value == null ? EMPTY : numberFormat.format(value);
}

/** A count with its noun: (1, "post") → "1 post", (1200, "post") → "1,200 posts" */
export function formatCount(count: number, singular: string, plural = `${singular}s`): string {
  return `${formatNumber(count)} ${count === 1 ? singular : plural}`;
}

/** A 0–1 fraction as a percentage: 0.8741 → "87.4%" */
export function formatPercent(fraction: number | null | undefined, digits = 1): string {
  if (fraction == null || Number.isNaN(fraction)) return EMPTY;
  return `${(fraction * 100).toFixed(digits)}%`;
}

/** Latency: 0.4 → "<1 ms", 14.3 → "14.3 ms", 1250 → "1.25 s" */
export function formatMs(ms: number | null | undefined): string {
  if (ms == null) return EMPTY;
  if (ms < 1) return "<1 ms";
  if (ms < 100) return `${ms.toFixed(1)} ms`;
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

/** Durations such as TTLs and uptime: 3700 → "1h 1m" */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return EMPTY;
  const s = Math.max(0, Math.round(seconds));
  const days = Math.floor(s / 86_400);
  const hours = Math.floor((s % 86_400) / 3_600);
  const minutes = Math.floor((s % 3_600) / 60);
  if (days > 0) return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
  if (hours > 0) return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  if (minutes > 0) return `${minutes}m`;
  return `${s}s`;
}

/** File sizes: 1536 → "1.5 KB", 1048576 → "1 MB" */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  // Number() drops trailing zeros: "1.00" → 1
  if (bytes < 1024 * 1024) return `${Number((bytes / 1024).toFixed(1))} KB`;
  return `${Number((bytes / (1024 * 1024)).toFixed(2))} MB`;
}

const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31_536_000],
  ["month", 2_592_000],
  ["week", 604_800],
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

/** "just now", "5 minutes ago", "yesterday" */
export function formatRelativeTime(iso: string, now: number): string {
  const seconds = (new Date(iso).getTime() - now) / 1000;
  if (Number.isNaN(seconds)) return EMPTY;
  if (Math.abs(seconds) < 45) return "just now";
  for (const [unit, size] of RELATIVE_UNITS) {
    if (Math.abs(seconds) >= size) return relativeFormat.format(Math.round(seconds / size), unit);
  }
  return relativeFormat.format(Math.round(seconds / 60), "minute");
}

/** Local date + time, e.g. "Oct 21, 2026, 2:03:12 PM" */
export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? EMPTY : dateTimeFormat.format(date);
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? EMPTY : dateFormat.format(date);
}

/** Axis label for a timeseries bucket at the summary's granularity. */
export function formatBucket(iso: string, granularity: "hour" | "day"): string {
  const date = new Date(iso);
  return granularity === "hour"
    ? date.toLocaleString("en", { month: "short", day: "numeric", hour: "numeric" })
    : date.toLocaleDateString("en", { month: "short", day: "numeric" });
}

/** "sentiment-logreg@1.2.0+ab12cd34" → "1.2.0+ab12cd34" (the full string goes in a title). */
export function shortVersion(version: string): string {
  const at = version.lastIndexOf("@");
  return at >= 0 ? version.slice(at + 1) : version;
}

/** Count characters the way the API does (Unicode code points, so an emoji is 1). */
export function countChars(text: string): number {
  return Array.from(text).length;
}

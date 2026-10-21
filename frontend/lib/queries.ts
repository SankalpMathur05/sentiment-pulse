import { keepPreviousData, queryOptions } from "@tanstack/react-query";
import {
  getAnalyticsSummary,
  getCacheStats,
  getHealth,
  getModelInfo,
  getPrediction,
  getPredictions,
} from "./api";
import { toApiParams, type Filters } from "./filters";

// Query keys and fetch functions in one place, so every view that shows the same
// data shares one cache entry, and mutations know exactly what to invalidate.

export const queryKeys = {
  health: ["health"] as const,
  model: ["model"] as const,
  cacheStats: ["cache-stats"] as const,
  analytics: ["analytics"] as const,
  predictions: ["predictions"] as const,
};

/** Everything a new prediction can change. */
export const PREDICTION_DEPENDENT_KEYS = [
  queryKeys.analytics,
  queryKeys.predictions,
  queryKeys.cacheStats,
];

const DASHBOARD_REFRESH_MS = 20_000;

export function healthQuery() {
  return queryOptions({
    queryKey: queryKeys.health,
    queryFn: ({ signal }) => getHealth(signal),
    refetchInterval: 30_000,
    retry: false,
  });
}

export function summaryQuery(filters: Filters, options: { live?: boolean } = {}) {
  return queryOptions({
    // The key holds the filters, not computed dates, so it stays stable while a
    // quick range like "last 24h" is re-evaluated on every refetch.
    queryKey: [...queryKeys.analytics, "summary", filters],
    queryFn: ({ signal }) => getAnalyticsSummary(toApiParams(filters), signal),
    placeholderData: keepPreviousData,
    refetchInterval: options.live ? DASHBOARD_REFRESH_MS : false,
  });
}

export function predictionsQuery(
  filters: Filters,
  page: number,
  pageSize: number,
  options: { live?: boolean } = {},
) {
  return queryOptions({
    queryKey: [...queryKeys.predictions, "list", { filters, page, pageSize }],
    queryFn: ({ signal }) =>
      getPredictions({ ...toApiParams(filters), page, page_size: pageSize }, signal),
    placeholderData: keepPreviousData,
    refetchInterval: options.live ? DASHBOARD_REFRESH_MS : false,
  });
}

export function predictionQuery(id: string) {
  return queryOptions({
    queryKey: [...queryKeys.predictions, "detail", id],
    queryFn: ({ signal }) => getPrediction(id, signal),
    staleTime: Infinity, // a stored prediction never changes
  });
}

export function cacheStatsQuery() {
  return queryOptions({
    queryKey: queryKeys.cacheStats,
    queryFn: ({ signal }) => getCacheStats(signal),
    refetchInterval: DASHBOARD_REFRESH_MS,
  });
}

export function modelQuery() {
  return queryOptions({
    queryKey: queryKeys.model,
    queryFn: ({ signal }) => getModelInfo(signal),
    staleTime: 5 * 60_000,
  });
}

"use client";

import { useSearchParams } from "next/navigation";
import { filtersToParams, parseFilters, type Filters } from "@/lib/filters";
import { useSearchParamsUpdater } from "./use-search-params-updater";

/** Dashboard/History filters, read from and written to the URL. */
export function useFilters() {
  const searchParams = useSearchParams();
  const updateSearchParams = useSearchParamsUpdater();

  const filters = parseFilters(searchParams);

  function setFilters(next: Filters) {
    // A different slice of data starts again from the first page.
    updateSearchParams({ ...filtersToParams(next), page: null });
  }

  return { filters, setFilters };
}

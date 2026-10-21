"use client";

import { usePathname, useSearchParams } from "next/navigation";

/**
 * Returns a function that merges updates into the URL's search params (null removes a
 * key). Uses history.replaceState, which Next.js syncs with useSearchParams, so the
 * view updates instantly without a server round trip or a new history entry.
 */
export function useSearchParamsUpdater() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  return (updates: Record<string, string | null>) => {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value) params.set(key, value);
      else params.delete(key);
    }
    const query = params.toString();
    window.history.replaceState(null, "", query ? `${pathname}?${query}` : pathname);
  };
}

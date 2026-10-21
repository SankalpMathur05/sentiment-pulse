"use client";

import { useEffect, useState } from "react";

/** The current time, refreshed on an interval, so relative times ("5 minutes ago") stay current. */
export function useNow(intervalMs = 30_000): number {
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return now;
}

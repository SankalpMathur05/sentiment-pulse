"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { isUnreachable } from "@/lib/api";
import { shouldRetry } from "@/lib/queries";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: 10_000, retry: shouldRetry },
      // A request that never reached the API (e.g. it was waking up) is safe to send again.
      mutations: { retry: (failureCount, error) => isUnreachable(error) && failureCount < 3 },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
  // Isolated per server render; one shared client for the lifetime of the browser tab.
  if (typeof window === "undefined") return makeQueryClient();
  browserQueryClient ??= makeQueryClient();
  return browserQueryClient;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={getQueryClient()}>
        <TooltipProvider delayDuration={200}>
          {children}
          <Toaster position="bottom-right" />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

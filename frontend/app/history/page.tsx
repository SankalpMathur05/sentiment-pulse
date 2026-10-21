import type { Metadata } from "next";
import { Suspense } from "react";
import { TableSkeleton } from "@/components/feedback/table-skeleton";
import { HistoryView } from "@/components/history/history-view";
import { PageContainer } from "@/components/layout/page";

export const metadata: Metadata = { title: "History" };

export default function HistoryPage() {
  return (
    // HistoryView reads filters and the page number from the URL (browser-only data).
    <Suspense
      fallback={
        <PageContainer>
          <TableSkeleton rows={10} />
        </PageContainer>
      }
    >
      <HistoryView />
    </Suspense>
  );
}

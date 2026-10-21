import type { Metadata } from "next";
import { Suspense } from "react";
import { DashboardSkeleton, DashboardView } from "@/components/dashboard/dashboard-view";
import { PageContainer } from "@/components/layout/page";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    // The view reads the URL's search params, which only exist in the browser request,
    // so the prerendered shell shows the skeleton until it renders.
    <Suspense
      fallback={
        <PageContainer>
          <DashboardSkeleton />
        </PageContainer>
      }
    >
      <DashboardView />
    </Suspense>
  );
}

"use client"; // Error boundaries must be Client Components

import { RotateCw, TriangleAlert } from "lucide-react";
import { EmptyState } from "@/components/feedback/empty-state";
import { PageContainer } from "@/components/layout/page";
import { Button } from "@/components/ui/button";

/** Last-resort boundary for unexpected rendering bugs (API failures are handled in each view). */
export default function ErrorBoundary({ retry }: { error: unknown; retry: () => void }) {
  return (
    <PageContainer>
      <EmptyState
        icon={TriangleAlert}
        title="Something went wrong"
        description="This page hit an unexpected error. Trying again usually fixes it."
        action={
          <Button variant="outline" size="sm" onClick={() => retry()}>
            <RotateCw />
            Try again
          </Button>
        }
      />
    </PageContainer>
  );
}

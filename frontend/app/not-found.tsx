import { Compass } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/feedback/empty-state";
import { PageContainer } from "@/components/layout/page";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <PageContainer>
      <EmptyState
        icon={Compass}
        title="Page not found"
        description="That page doesn't exist. Head back and analyze a post instead."
        action={
          <Button asChild size="sm">
            <Link href="/">Go to Analyze</Link>
          </Button>
        }
      />
    </PageContainer>
  );
}

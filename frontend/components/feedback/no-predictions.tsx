import { ScanText, SearchX, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState } from "./empty-state";

/**
 * Empty state for views of stored predictions. With filters active the fix is to widen
 * them; with no predictions at all, the next step is to analyze a post.
 */
export function NoPredictions({
  filtered,
  onResetFilters,
  icon,
  description,
  className,
}: {
  filtered: boolean;
  onResetFilters: () => void;
  icon: LucideIcon;
  /** What will appear here once there are predictions. */
  description: string;
  className?: string;
}) {
  if (filtered) {
    return (
      <EmptyState
        icon={SearchX}
        title="No predictions match these filters"
        description="Try a wider date range or a different sentiment."
        className={className}
        action={
          <Button variant="outline" size="sm" onClick={onResetFilters}>
            Reset filters
          </Button>
        }
      />
    );
  }
  return (
    <EmptyState
      icon={icon}
      title="No predictions yet"
      description={description}
      className={className}
      action={
        <Button asChild size="sm">
          <Link href="/">
            <ScanText />
            Analyze a post
          </Link>
        </Button>
      }
    />
  );
}

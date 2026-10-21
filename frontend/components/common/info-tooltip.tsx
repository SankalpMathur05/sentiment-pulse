import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/** A small focusable (i) icon that explains a term. */
export function InfoTooltip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger
        type="button"
        aria-label={label}
        className="inline-flex size-4 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        <Info className="size-3.5" />
      </TooltipTrigger>
      <TooltipContent className="max-w-64 text-balance">{children}</TooltipContent>
    </Tooltip>
  );
}

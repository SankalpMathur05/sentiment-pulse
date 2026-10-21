import { cn } from "@/lib/utils";

/** A pulse line in a rounded square. Uses theme colours, so it inverts in dark mode. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={cn("size-7 shrink-0", className)}>
      <rect width="32" height="32" rx="8" className="fill-foreground" />
      <path
        d="M6 17h4.5l2.5-6.5 4.5 12 3-8 1.75 2.5H26"
        fill="none"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="stroke-background"
      />
    </svg>
  );
}

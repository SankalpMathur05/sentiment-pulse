import { cn } from "@/lib/utils";

/** Centred, padded content column used by every page. */
export function PageContainer({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 md:px-8 md:py-8", className)}>
      {children}
    </div>
  );
}

/** One-line explanation of the page, with optional page-level actions on the right. */
export function PageIntro({
  children,
  actions,
}: {
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="max-w-2xl text-sm text-pretty text-muted-foreground">{children}</p>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

import { SENTIMENT_STYLES } from "@/lib/sentiment";
import type { Sentiment } from "@/lib/types";
import { cn } from "@/lib/utils";

const SIZES = {
  sm: "h-5 gap-1 px-1.5 text-xs [&_svg]:size-3",
  md: "h-6 gap-1.5 px-2 text-xs [&_svg]:size-3.5",
  lg: "h-9 gap-2 px-3.5 text-base font-semibold [&_svg]:size-5",
};

/** Sentiment shown as colour + icon + word, so it never relies on colour alone. */
export function SentimentBadge({
  sentiment,
  size = "md",
  className,
}: {
  sentiment: Sentiment;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const { label, icon: Icon, badgeClass } = SENTIMENT_STYLES[sentiment];
  return (
    <span
      className={cn(
        "inline-flex w-fit shrink-0 items-center rounded-full font-medium whitespace-nowrap ring-1 ring-inset",
        badgeClass,
        SIZES[size],
        className,
      )}
    >
      <Icon />
      {label}
    </span>
  );
}

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SentimentBadge } from "@/components/sentiment/sentiment-badge";

describe("SentimentBadge", () => {
  it.each([
    ["positive", "Positive", "lucide-smile"],
    ["negative", "Negative", "lucide-frown"],
    ["neutral", "Neutral", "lucide-meh"],
  ] as const)("shows %s with its label and icon", (sentiment, label, iconClass) => {
    const { container } = render(<SentimentBadge sentiment={sentiment} />);

    expect(screen.getByText(label)).toBeInTheDocument();
    expect(container.querySelector("svg")).toHaveClass(iconClass);
  });
});

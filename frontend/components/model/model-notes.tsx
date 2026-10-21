import { TriangleAlert } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function Limitations({ items }: { items: string[] }) {
  return (
    <Card className="bg-warning/5 ring-warning/25">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TriangleAlert className="size-4 text-warning-ink" aria-hidden />
          Known limitations
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="grid list-disc gap-2 pl-5 text-sm text-pretty marker:text-muted-foreground">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

/** Plain-language definitions for the metrics on this page. */
export function HowToRead({ logLoss, brier }: { logLoss: number; brier: number }) {
  const terms = [
    ["Precision", "Of the posts the model called X, how many really were X."],
    ["Recall", "Of the posts that really were X, how many the model caught."],
    ["F1", "The balance of precision and recall (their harmonic mean)."],
    [
      "Macro average",
      "The plain average over classes, so small classes count as much as large ones.",
    ],
    [
      "Calibration",
      `Log loss ${logLoss.toFixed(3)} and Brier score ${brier.toFixed(3)} (lower is better) measure how trustworthy the confidence values are.`,
    ],
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>How to read this</CardTitle>
        <CardDescription>
          All numbers come from a test set the model never saw in training.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-3 text-sm">
          {terms.map(([term, definition]) => (
            <div key={term} className="grid gap-0.5 sm:grid-cols-[8rem_1fr] sm:gap-3">
              <dt className="font-medium">{term}</dt>
              <dd className="text-muted-foreground">{definition}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

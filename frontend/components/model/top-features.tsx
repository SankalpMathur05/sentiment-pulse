import { TopWordChips } from "@/components/sentiment/top-word-chips";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { isSentiment } from "@/lib/sentiment";
import type { TopWord } from "@/lib/types";
import { ClassLabel, orderedLabels } from "./class-label";

/** One column of the model's strongest words per class. */
export function TopFeatures({ features }: { features: Record<string, TopWord[]> }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Words the model associates with each sentiment</CardTitle>
        <CardDescription>
          The strongest weights the model learned for each class, across all training data.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 md:grid-cols-3">
        {orderedLabels(Object.keys(features)).map((label) => (
          <div key={label} className="grid content-start gap-3">
            <ClassLabel label={label} />
            <TopWordChips
              words={features[label]}
              sentiment={isSentiment(label) ? label : "neutral"}
            />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

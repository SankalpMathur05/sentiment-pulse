"use client";

import { useQuery } from "@tanstack/react-query";
import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer, PageIntro } from "@/components/layout/page";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { modelQuery } from "@/lib/queries";
import type { ModelInfo } from "@/lib/types";
import { ClassMetricsTable } from "./class-metrics-table";
import { ComparisonTable } from "./comparison-table";
import { ConfusionMatrix } from "./confusion-matrix";
import { HowToRead, Limitations } from "./model-notes";
import { ModelOverview } from "./model-overview";
import { TopFeatures } from "./top-features";

export function ModelView() {
  const { data, error, isPending, isFetching, refetch } = useQuery(modelQuery());

  let content: React.ReactNode;
  if (isPending) content = <ModelSkeleton />;
  else if (error && !data) {
    content = <ErrorState error={error} onRetry={() => refetch()} retrying={isFetching} />;
  } else content = <ModelDetails model={data} />;

  return (
    <PageContainer>
      <PageIntro>
        The model behind every prediction: how it was trained, how well it does on posts it never
        saw, and where it falls short.
      </PageIntro>
      {content}
    </PageContainer>
  );
}

function ModelDetails({ model }: { model: ModelInfo }) {
  const { metrics } = model;
  return (
    <>
      <ModelOverview model={model} />

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <ClassMetricsTable perClass={metrics.per_class} />
        <Card>
          <CardHeader>
            <CardTitle>Confusion matrix</CardTitle>
            <CardDescription>Where test posts landed. The diagonal is correct.</CardDescription>
          </CardHeader>
          <CardContent>
            <ConfusionMatrix matrix={metrics.confusion_matrix} labels={metrics.confusion_labels} />
          </CardContent>
        </Card>
      </div>

      <ComparisonTable rows={model.comparison} />
      <TopFeatures features={model.top_features} />

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <Limitations items={model.limitations} />
        <HowToRead logLoss={metrics.log_loss} brier={metrics.brier_score} />
      </div>
    </>
  );
}

function ModelSkeleton() {
  return (
    <div className="grid gap-6" aria-busy aria-label="Loading model details">
      <Skeleton className="h-28 rounded-xl" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    </div>
  );
}

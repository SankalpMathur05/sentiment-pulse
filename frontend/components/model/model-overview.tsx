import { Award, BrainCircuit, Crosshair, ExternalLink, Radar, Target } from "lucide-react";
import { CopyButton } from "@/components/common/copy-button";
import { InfoTooltip } from "@/components/common/info-tooltip";
import { StatCard } from "@/components/common/stat-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate, formatNumber, formatPercent } from "@/lib/format";
import type { ModelInfo } from "@/lib/types";

/** Name, version, training facts and the four headline test-set metrics. */
export function ModelOverview({ model }: { model: ModelInfo }) {
  const { metrics, dataset } = model;

  return (
    <>
      <Card>
        <CardContent className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div className="flex gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted">
              <BrainCircuit className="size-5 text-muted-foreground" aria-hidden />
            </span>
            <div className="grid gap-1">
              <h2 className="text-lg font-semibold tracking-tight">{model.name}</h2>
              <div className="flex flex-wrap items-center gap-1">
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs whitespace-nowrap">
                  {model.version}
                </code>
                <CopyButton value={model.version} label="Copy model version" />
              </div>
            </div>
          </div>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-3">
            <Fact label="Trained">{formatDate(model.trained_at)}</Fact>
            <Fact label="Dataset">
              <a
                href={dataset.homepage}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 underline-offset-4 hover:underline"
              >
                {dataset.name}
                <ExternalLink className="size-3" aria-hidden />
              </a>
            </Fact>
            <Fact label="Licence">{dataset.licence}</Fact>
            <Fact label="Train / test rows">
              {formatNumber(dataset.rows_train)} / {formatNumber(dataset.rows_test)}
            </Fact>
            <Fact label="scikit-learn">
              <span className="font-mono text-xs">{model.sklearn_version}</span>
            </Fact>
            <Fact label="Low-confidence below">
              {formatPercent(model.low_confidence_threshold, 0)}
            </Fact>
          </dl>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          icon={Target}
          label="Accuracy"
          value={formatPercent(metrics.accuracy)}
          sub={`on ${formatNumber(dataset.rows_test)} held-out posts`}
        />
        <StatCard
          icon={Award}
          label="Macro-F1"
          value={formatPercent(metrics.macro_f1)}
          sub={`weighted F1 ${formatPercent(metrics.weighted_f1)}`}
          badge={
            <span className="flex items-center gap-1">
              <Badge variant="secondary" className="h-4.5 px-1.5 text-[10px]">
                headline metric
              </Badge>
              <InfoTooltip label="Why macro-F1 is the headline metric">
                Macro-F1 gives every class an equal vote, so the 64% negative majority can&apos;t
                hide poor neutral or positive performance the way accuracy can.
              </InfoTooltip>
            </span>
          }
        />
        <StatCard
          icon={Crosshair}
          label="Macro precision"
          value={formatPercent(metrics.macro_precision)}
          sub="averaged over the classes"
        />
        <StatCard
          icon={Radar}
          label="Macro recall"
          value={formatPercent(metrics.macro_recall)}
          sub="averaged over the classes"
        />
      </div>
    </>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  );
}

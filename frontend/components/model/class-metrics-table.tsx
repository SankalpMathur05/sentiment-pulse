import { TableCard } from "@/components/common/table-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatNumber, formatPercent } from "@/lib/format";
import { isSentiment, SENTIMENT_STYLES } from "@/lib/sentiment";
import type { ClassMetrics } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ClassLabel, orderedLabels } from "./class-label";

export function ClassMetricsTable({ perClass }: { perClass: Record<string, ClassMetrics> }) {
  return (
    <TableCard
      title="Per-class performance"
      description="Test set. Support is how many test posts had that label."
    >
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Class</TableHead>
            <TableHead className="text-right">Precision</TableHead>
            <TableHead className="text-right">Recall</TableHead>
            <TableHead>F1</TableHead>
            <TableHead className="text-right">Support</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orderedLabels(Object.keys(perClass)).map((label) => {
            const m = perClass[label];
            return (
              <TableRow key={label} className="hover:bg-transparent">
                <TableCell>
                  <ClassLabel label={label} />
                </TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">
                  {formatPercent(m.precision)}
                </TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">
                  {formatPercent(m.recall)}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted" aria-hidden>
                      <div
                        className={cn(
                          "h-full rounded-full",
                          isSentiment(label) ? SENTIMENT_STYLES[label].fillClass : "bg-foreground",
                        )}
                        style={{ width: `${m.f1 * 100}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs font-medium tabular-nums">
                      {formatPercent(m.f1)}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-right font-mono text-xs text-muted-foreground tabular-nums">
                  {formatNumber(m.support)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableCard>
  );
}

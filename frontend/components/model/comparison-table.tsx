import { TableCard } from "@/components/common/table-card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatPercent } from "@/lib/format";
import type { ModelComparisonRow } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Every candidate model that was evaluated, with the one being served highlighted. */
export function ComparisonTable({ rows }: { rows: ModelComparisonRow[] }) {
  return (
    <TableCard
      title="Model comparison"
      description="Candidates scored with cross-validation on the training set, then once on the test set."
    >
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Model</TableHead>
            <TableHead className="text-right">CV macro-F1</TableHead>
            <TableHead className="text-right">Test macro-F1</TableHead>
            <TableHead className="text-right">Test accuracy</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow
              key={row.model}
              className={cn("hover:bg-transparent", row.selected && "bg-muted/60")}
            >
              <TableCell className="font-medium">
                <span className="flex items-center gap-2">
                  {row.model}
                  {row.selected && <Badge className="h-4.5 px-1.5 text-[10px]">served</Badge>}
                </span>
              </TableCell>
              <TableCell className="text-right font-mono text-xs tabular-nums">
                {formatPercent(row.cv_macro_f1)}
                <span className="text-muted-foreground">
                  {" "}
                  ± {formatPercent(row.cv_macro_f1_std)}
                </span>
              </TableCell>
              <TableCell className="text-right font-mono text-xs tabular-nums">
                {formatPercent(row.test_macro_f1)}
              </TableCell>
              <TableCell className="text-right font-mono text-xs tabular-nums">
                {formatPercent(row.test_accuracy)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableCard>
  );
}

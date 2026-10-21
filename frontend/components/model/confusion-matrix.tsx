import { formatNumber, formatPercent } from "@/lib/format";
import { isSentiment, SENTIMENT_STYLES } from "@/lib/sentiment";
import { cn } from "@/lib/utils";

function labelFor(label: string) {
  return isSentiment(label) ? SENTIMENT_STYLES[label].label : label;
}

/**
 * Rows are the true label, columns the predicted one. Each cell shows its count and
 * its share of the row (that class's recall on the diagonal); a deeper tint means a
 * larger share, using a single hue so intensity reads as "more".
 */
export function ConfusionMatrix({ matrix, labels }: { matrix: number[][]; labels: string[] }) {
  const rowTotals = matrix.map((row) => row.reduce((sum, n) => sum + n, 0));

  return (
    <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-2">
      <div className="row-start-2 flex items-center">
        <span className="rotate-180 text-xs font-medium text-muted-foreground [writing-mode:vertical-rl]">
          True label
        </span>
      </div>
      <p className="col-start-2 text-center text-xs font-medium text-muted-foreground">
        Predicted label
      </p>

      <table className="col-start-2 w-full table-fixed border-separate border-spacing-1 text-sm">
        <caption className="sr-only">
          Confusion matrix on the test set. Rows are true labels, columns are predicted labels.
        </caption>
        <thead>
          <tr>
            <td className="w-20" />
            {labels.map((label) => (
              <th
                key={label}
                scope="col"
                className="pb-1 text-xs font-medium text-muted-foreground"
              >
                {labelFor(label)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={labels[i]}>
              <th scope="row" className="pr-2 text-right text-xs font-medium text-muted-foreground">
                {labelFor(labels[i])}
              </th>
              {row.map((count, j) => {
                const share = rowTotals[i] ? count / rowTotals[i] : 0;
                return (
                  <td
                    key={labels[j]}
                    className={cn(
                      "h-16 rounded-md text-center align-middle ring-1 ring-foreground/5 ring-inset",
                      // Switch to light text once the tint is dark enough to need it.
                      share > 0.5 ? "text-white" : "text-foreground",
                      i === j && "ring-2 ring-foreground/15",
                    )}
                    style={{
                      backgroundColor: `color-mix(in oklch, var(--heat) ${Math.round(share * 85)}%, transparent)`,
                    }}
                  >
                    <span className="block font-semibold tabular-nums">{formatNumber(count)}</span>
                    <span
                      className={cn(
                        "block text-[11px] tabular-nums",
                        share > 0.5 ? "text-white/80" : "text-muted-foreground",
                      )}
                    >
                      {formatPercent(share)}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

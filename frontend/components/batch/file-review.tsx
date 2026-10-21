"use client";

import { CircleAlert, FileText, TriangleAlert, X } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CsvInspection } from "@/lib/csv";
import { formatBytes, formatCount } from "@/lib/format";

/** The chosen file: its size and row count, any validation problem, and a preview. */
export function FileReview({
  file,
  inspection,
  onRemove,
  disabled,
}: {
  file: File;
  inspection: CsvInspection;
  onRemove: () => void;
  disabled: boolean;
}) {
  return (
    <div className="grid gap-4">
      <div className="flex items-center gap-3 rounded-lg p-3 ring-1 ring-border">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted">
          <FileText className="size-4 text-muted-foreground" aria-hidden />
        </span>
        <div className="grid min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{file.name}</p>
          <p className="text-xs text-muted-foreground">
            {formatBytes(file.size)}
            {inspection.rowCount > 0 && ` · ${formatCount(inspection.rowCount, "row")}`}
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onRemove}
          disabled={disabled}
          aria-label="Remove file"
        >
          <X />
        </Button>
      </div>

      {inspection.error ? (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertTitle>This file can&apos;t be uploaded</AlertTitle>
          <AlertDescription>{inspection.error}</AlertDescription>
        </Alert>
      ) : (
        <>
          {inspection.emptyTextRows > 0 && (
            <p className="flex items-center gap-2 text-xs text-warning-ink">
              <TriangleAlert className="size-3.5 shrink-0" aria-hidden />
              {formatCount(inspection.emptyTextRows, "row")} with empty text will be reported as
              failed.
            </p>
          )}
          <div className="grid gap-2">
            <p className="text-xs font-medium text-muted-foreground">
              Preview · first {inspection.preview.length} of{" "}
              {formatCount(inspection.rowCount, "row")}
            </p>
            <div className="overflow-hidden rounded-lg ring-1 ring-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">Row</TableHead>
                    <TableHead>text</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {inspection.preview.map((text, i) => (
                    <TableRow key={i} className="hover:bg-transparent">
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {i + 1}
                      </TableCell>
                      <TableCell className="max-w-0 truncate" title={text}>
                        {text || <span className="text-muted-foreground italic">empty</span>}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

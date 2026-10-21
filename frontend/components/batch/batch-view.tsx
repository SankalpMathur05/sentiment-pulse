"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, Download, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { PageContainer, PageIntro } from "@/components/layout/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { ApiError, predictBatch } from "@/lib/api";
import { downloadCsv, inspectCsv, sampleCsv, type CsvInspection } from "@/lib/csv";
import { describeError } from "@/lib/errors";
import { formatCount, formatNumber } from "@/lib/format";
import { PREDICTION_DEPENDENT_KEYS } from "@/lib/queries";
import { BatchResults } from "./batch-results";
import { Dropzone } from "./dropzone";
import { FileReview } from "./file-review";

interface SelectedFile {
  file: File;
  inspection: CsvInspection;
}

export function BatchView() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<SelectedFile | null>(null);
  const [isReading, setIsReading] = useState(false);

  const mutation = useMutation({
    mutationFn: (file: File) => predictBatch(file),
    onSuccess: (result) => {
      for (const queryKey of PREDICTION_DEPENDENT_KEYS) {
        void queryClient.invalidateQueries({ queryKey });
      }
      toast.success(
        `Analyzed ${formatNumber(result.succeeded)} of ${formatCount(result.total_rows, "post")}`,
      );
    },
    onError: (error) => {
      const { title, message } = describeError(error);
      toast.error(title, { description: message });
    },
  });

  async function selectFile(file: File) {
    mutation.reset();
    setIsReading(true);
    setSelected({ file, inspection: await inspectCsv(file) });
    setIsReading(false);
  }

  function reset() {
    mutation.reset();
    setSelected(null);
  }

  const canUpload = selected !== null && !selected.inspection.error && !mutation.isPending;
  const rowCount = selected?.inspection.rowCount ?? 0;

  return (
    <PageContainer>
      <PageIntro
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadCsv("sentiment-pulse-sample.csv", sampleCsv())}
          >
            <Download />
            Download sample CSV
          </Button>
        }
      >
        Analyze up to 500 posts at once. Files are checked in your browser first, so problems show
        up before anything is uploaded.
      </PageIntro>

      {mutation.data ? (
        <BatchResults result={mutation.data} onReset={reset} />
      ) : (
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_19rem]">
          <Card>
            <CardHeader>
              <CardTitle>Upload a CSV</CardTitle>
              <CardDescription>You&apos;ll see a preview before anything is sent.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              {selected ? (
                <FileReview
                  file={selected.file}
                  inspection={selected.inspection}
                  onRemove={reset}
                  disabled={mutation.isPending}
                />
              ) : (
                <Dropzone onFile={selectFile} disabled={isReading} />
              )}

              {mutation.isPending && selected && (
                <div className="grid gap-2" role="status">
                  {/* Indeterminate: fetch can't report upload or server progress. */}
                  <div className="h-1 overflow-hidden rounded-full bg-muted" aria-hidden>
                    <div className="h-full w-1/3 animate-indeterminate rounded-full bg-primary motion-reduce:w-full motion-reduce:animate-pulse" />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Uploading and analyzing {formatCount(rowCount, "post")}. This usually takes a
                    few seconds.
                  </p>
                </div>
              )}

              {mutation.error && <UploadError error={mutation.error} />}
            </CardContent>
            {selected && (
              <CardFooter className="justify-end gap-2">
                <Button variant="ghost" onClick={reset} disabled={mutation.isPending}>
                  Cancel
                </Button>
                <Button onClick={() => mutation.mutate(selected.file)} disabled={!canUpload}>
                  {mutation.isPending ? <Spinner /> : <Sparkles />}
                  {mutation.isPending ? "Analyzing…" : "Upload & analyze"}
                </Button>
              </CardFooter>
            )}
          </Card>
          <FormatHelp />
        </div>
      )}
    </PageContainer>
  );
}

function FormatHelp() {
  const example = [
    "text",
    '"Best flight ever, thank you!"',
    '"Is there wifi on board?"',
    '"Lost my bag again 🙄"',
  ];
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>File format</CardTitle>
        <CardDescription>A header row, then one post per row.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <pre className="overflow-x-auto rounded-lg bg-muted/60 p-3 font-mono text-xs leading-relaxed">
          {example.join("\n")}
        </pre>
        <ul className="grid list-disc gap-1.5 pl-4 text-sm text-muted-foreground marker:text-muted-foreground/60">
          <li>A column named “text” (other columns are ignored)</li>
          <li>Up to 500 rows and 1 MB</li>
          <li>Rows that can&apos;t be analyzed are reported one by one, not dropped</li>
        </ul>
      </CardContent>
    </Card>
  );
}

/** The API rejected the upload: friendly title, any per-field messages, and the request id. */
function UploadError({ error }: { error: unknown }) {
  const { title, message, requestId } = describeError(error);
  const details = error instanceof ApiError ? error.details : [];
  return (
    <Alert variant="destructive">
      <CircleAlert />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <p>{message}</p>
        {details.length > 0 && (
          <ul className="list-disc pl-4">
            {details.map((detail, i) => (
              <li key={i}>
                {detail.field && <span className="font-medium">{detail.field}: </span>}
                {detail.message}
              </li>
            ))}
          </ul>
        )}
        {requestId && <p className="font-mono text-xs">Request ID {requestId}</p>}
      </AlertDescription>
    </Alert>
  );
}
